#!/bin/bash
set -x

function main {

  init_params "$@"
  run_tuning

}

# init params
function init_params {
  output_model=saved_results
  for var in "$@"
  do
    case $var in
      --topology=*)
          topology=$(echo $var |cut -f2 -d=)
      ;;
      --dataset_location=*)
          dataset_location=$(echo $var |cut -f2 -d=)
      ;;
      --input_model=*)
          input_model=$(echo $var |cut -f2 -d=)
      ;;
      --output_model=*)
          output_model=$(echo $var |cut -f2 -d=)
      ;;
      *)
          echo "Error: No such parameter: ${var}"
          exit 1
      ;;
    esac
  done

}

# run_tuning
function run_tuning {
    extra_cmd=""
    if [ -n "$output_model" ];then
        extra_cmd = $extra_cmd"--tuned_checkpoint ${output_model}"
    fi
    extra_cmd=$extra_cmd" ${dataset_location}"

    python main.py \
            --pretrained \
            -t \
            -a $input_model \
            -j 1 \
            -b 128 \
            ${extra_cmd}

}

main "$@"
