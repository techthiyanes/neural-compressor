Step-by-Step
============

This document is used to list steps of reproducing TensorFlow Object Detection models tuning results. This example can run on Intel CPUs and GPUs.

# Prerequisite


## 1. Environment
Recommend python 3.6 or higher version.

### Install Intel® Neural Compressor
```shell
pip install neural-compressor
```

### Install Intel Tensorflow
```shell
pip install intel-tensorflow
```
> Note: Supported Tensorflow [Version](../../../../../../README.md#supported-frameworks).

### Installation Dependency packages
```shell
cd examples/tensorflow/object_detection/tensorflow_models/
pip install -r requirements.txt
cd ssd_resnet34/quantization/ptq
```

### Install Protocol Buffer Compiler

`Protocol Buffer Compiler` in version higher than 3.0.0 is necessary ingredient for automatic COCO dataset preparation. To install please follow
[Protobuf installation instructions](https://grpc.io/docs/protoc-installation/#install-using-a-package-manager).

### Install Intel Extension for Tensorflow

#### Quantizing the model on Intel GPU
Intel Extension for Tensorflow is mandatory to be installed for quantizing the model on Intel GPUs.

```shell
pip install --upgrade intel-extension-for-tensorflow[gpu]
```
For any more details, please follow the procedure in [install-gpu-drivers](https://github.com/intel-innersource/frameworks.ai.infrastructure.intel-extension-for-tensorflow.intel-extension-for-tensorflow/blob/master/docs/install/install_for_gpu.md#install-gpu-drivers)

#### Quantizing the model on Intel CPU(Experimental)
Intel Extension for Tensorflow for Intel CPUs is experimental currently. It's not mandatory for quantizing the model on Intel CPUs.

```shell
pip install --upgrade intel-extension-for-tensorflow[cpu]
```

## 2. Prepare Model

```shell
wget https://storage.googleapis.com/intel-optimized-tensorflow/models/v1_8/ssd_resnet34_fp32_1200x1200_pretrained_model.pb
```

## 3. Prepare Dataset

### Automatic dataset download

> **_Note: `prepare_dataset.sh` script works with TF version 1.x._**

Run the `prepare_dataset.sh` script located in `examples/tensorflow/object_detection/tensorflow_models/quantization/ptq`.

Usage:
```shell
cd examples/tensorflow/object_detection/tensorflow_models/
. prepare_dataset.sh
cd ssd_resnet34/quantization/ptq
```

This script will download the *train*, *validation* and *test* COCO datasets. Furthermore it will convert them to
tensorflow records using the `https://github.com/tensorflow/models.git` dedicated script.

### Manual dataset download
Download CoCo Dataset from [Official Website](https://cocodataset.org/#download).


# Run

## 1. Tune
  
  ```shell
  # The cmd of running ssd_resnet34
  bash run_tuning.sh --input_model=./ssd_resnet34_fp32_1200x1200_pretrained_model.pb --output_model=./tensorflow-ssd_resnet34-tune.pb --dataset_location=/path/to/dataset/coco_val.record --anno_path=./label_map.yaml
  ```

## 2. Benchmark
  ```shell
  bash run_benchmark.sh --input_model=./tensorflow-ssd_resnet34-tune.pb  --dataset_location=/path/to/dataset/coco_val.record --mode=performance
  ```

Details of enabling Intel® Neural Compressor on ssd_resnet34 for Tensorflow.
=========================

This is a tutorial of how to enable ssd_resnet34 model with Intel® Neural Compressor.
## User Code Analysis
User specifies fp32 *model*, calibration dataset *q_dataloader* and a custom *eval_func* which encapsulates the evaluation dataset and metric by itself.

For ssd_resnet34, we applied the latter one because our philosophy is to enable the model with minimal changes. Hence we need to make two changes on the original code. The first one is to implement the q_dataloader and make necessary changes to *eval_func*.

### Code update

After prepare step is done, we just need update main.py like below.
```python
    if args.tune:
        from neural_compressor import quantization
        from neural_compressor.config import PostTrainingQuantConfig, AccuracyCriterion
        accuracy_criterion = AccuracyCriterion(criterion='absolute')
        config = PostTrainingQuantConfig(
            inputs=["image"],
            outputs=["detection_bboxes", "detection_scores", "detection_classes"],
            calibration_sampling_size=[100],
            accuracy_criterion=accuracy_criterion)
        q_model = quantization.fit(model=args.input_graph, conf=config, 
                                    calib_dataloader=calib_dataloader, eval_func=evaluate)
        q_model.save(args.output_model)
            
    if args.benchmark:
        from neural_compressor.benchmark import fit
        from neural_compressor.config import BenchmarkConfig
        if args.mode == 'performance':
            conf = BenchmarkConfig(cores_per_instance=28, num_of_instance=1)
            fit(args.input_graph, conf, b_func=evaluate)
        else:
            accuracy = evaluate(args.input_graph)
            print('Batch size = %d' % args.batch_size)
            print("Accuracy: %.5f" % accuracy)
```

The quantization.fit() function will return a best quantized model during timeout constrain.
