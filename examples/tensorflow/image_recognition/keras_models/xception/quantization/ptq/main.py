#
# -*- coding: utf-8 -*-
#
# Copyright (c) 2018 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import time
import numpy as np
import tensorflow as tf
from neural_compressor.utils import logger
tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.ERROR)

flags = tf.compat.v1.flags
FLAGS = flags.FLAGS

## Required parameters
flags.DEFINE_string(
    'input_model', None, 'Run inference with specified keras model.')

flags.DEFINE_string(
    'output_model', None, 'The output quantized model.')

flags.DEFINE_string(
    'mode', 'performance', 'define benchmark mode for accuracy or performance')

flags.DEFINE_bool(
    'tune', False, 'whether to tune the model')

flags.DEFINE_bool(
    'benchmark', False, 'whether to benchmark the model')

flags.DEFINE_string(
    'calib_data', None, 'location of calibration dataset')

flags.DEFINE_string(
    'eval_data', None, 'location of evaluate dataset')

flags.DEFINE_integer('batch_size', 32, 'batch_size')

flags.DEFINE_integer(
    'iters', 100, 'maximum iteration when evaluating performance')

from neural_compressor.metric import TensorflowTopK
from neural_compressor.data import ComposeTransform
from neural_compressor.data import TensorflowImageRecord
from neural_compressor.data import LabelShift
from neural_compressor.data import DefaultDataLoader
from neural_compressor.data import BilinearImagenetTransform

eval_dataset = TensorflowImageRecord(root=FLAGS.eval_data, transform=ComposeTransform(transform_list= \
                [BilinearImagenetTransform(height=299, width=299)]))

eval_dataloader = DefaultDataLoader(dataset=eval_dataset, batch_size=FLAGS.batch_size)


if FLAGS.calib_data:
    calib_dataset = TensorflowImageRecord(root=FLAGS.calib_data, transform= \
        ComposeTransform(transform_list= [BilinearImagenetTransform(height=299, width=299)]))
    calib_dataloader = DefaultDataLoader(dataset=calib_dataset, batch_size=10)

def evaluate(model):
    """
    Custom evaluate function to inference the model for specified metric on validation dataset.

    Args:
        model (tf.saved_model.load): The input model will be the class of tf.saved_model.load(quantized_model_path).
        measurer (object, optional): for benchmark measurement of duration.

    Returns:
        accuracy (float): evaluation result, the larger is better.
    """
    infer = model.signatures["serving_default"]
    output_dict_keys = infer.structured_outputs.keys()
    output_name = list(output_dict_keys )[0]
    postprocess = LabelShift(label_shift=1)
    metric = TensorflowTopK(k=1)
    latency_list = []

    def eval_func(dataloader, metric):
        warmup = 5
        iteration = None

        if FLAGS.benchmark and FLAGS.mode == 'performance':
            iteration = FLAGS.iters
        for idx, (inputs, labels) in enumerate(dataloader):
            inputs = np.array(inputs)
            input_tensor = tf.constant(inputs)
            start = time.time()
            predictions = infer(input_tensor)[output_name]
            end = time.time()
            latency_list.append(end - start)
            predictions = predictions.numpy()
            predictions, labels = postprocess((predictions, labels))
            metric.update(predictions, labels)
            if iteration and idx >= iteration:
                break
        latency = np.array(latency_list[warmup:]).mean() / eval_dataloader.batch_size
        return latency

    latency = eval_func(eval_dataloader, metric)
    if FLAGS.benchmark:
        logger.info("\n{} mode benchmark result:".format(FLAGS.mode))
        for i, res in enumerate(latency_list):
            logger.debug("Iteration {} result {}:".format(i, res))
    if FLAGS.benchmark and FLAGS.mode == 'performance':
        print("Batch size = {}".format(eval_dataloader.batch_size))
        print("Latency: {:.3f} ms".format(latency * 1000))
        print("Throughput: {:.3f} images/sec".format(1. / latency))
    acc = metric.result()
    return acc

def main(_):
    if FLAGS.tune:
        from neural_compressor.quantization import fit
        from neural_compressor.config import PostTrainingQuantConfig
        from neural_compressor.utils import set_random_seed
        set_random_seed(9527)
        config = PostTrainingQuantConfig(calibration_sampling_size=[50, 100])
        q_model = fit(
            model=FLAGS.input_model,
            conf=config,
            calib_dataloader=calib_dataloader,
            eval_dataloader=eval_dataloader,
            eval_func=evaluate)
        q_model.save(FLAGS.output_model)

    if FLAGS.benchmark:
        from neural_compressor.benchmark import fit
        from neural_compressor.config import BenchmarkConfig
        if FLAGS.mode == 'performance':
            conf = BenchmarkConfig(iteration=100, cores_per_instance=4, num_of_instance=7)
            fit(FLAGS.input_model, conf, b_func=evaluate)
        else:
            from neural_compressor.model import Model
            accuracy = evaluate(Model(FLAGS.input_model).model)
            print('Batch size = %d' % FLAGS.batch_size)
            print("Accuracy: %.5f" % accuracy)

if __name__ == "__main__":
    tf.compat.v1.app.run()
