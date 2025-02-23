# Test the LLMEngine with multi-step-decoding
from typing import Optional

import pytest

from ..models.utils import check_logprobs_close, check_outputs_equal

MODELS = [
    "JackFram/llama-160m",
]
NUM_SCHEDULER_STEPS = [8]  # Multi-step decoding steps
NUM_PROMPTS = [10]


@pytest.mark.parametrize("model", MODELS)
@pytest.mark.parametrize("dtype", ["half"])
@pytest.mark.parametrize("tp_size", [1])
@pytest.mark.parametrize("max_tokens", [5])
@pytest.mark.parametrize("enforce_eager", [True])
@pytest.mark.parametrize("num_scheduler_steps", NUM_SCHEDULER_STEPS)
@pytest.mark.parametrize("num_prompts", NUM_PROMPTS)
@pytest.mark.parametrize("num_logprobs", [None, 5])
def test_multi_step_llm(
    hf_runner,
    aphrodite_runner,
    example_prompts,
    model: str,
    dtype: str,
    tp_size: int,
    max_tokens: int,
    enforce_eager: int,
    num_scheduler_steps: int,
    num_prompts: int,
    num_logprobs: Optional[int],
) -> None:
    """Test Aphrodite engine with multi-step scheduling via sync LLM Engine.
    Set up a HuggingFace (HF) transformers model as a ground-truth reference.
    Prompt them with the same example prompts.
    Validate:
    * Generated tokens match
    * Generated logprobs are all very close
    Args:
      hf_runner: HF transformers model runner fixture
      aphrodite_runner: Aphrodite model runner fixture
      example_prompts: test fixture providing example prompts
      model: model under test (same for single- and multi-step engines)
      dtype: tensor datatype for engine to utilize
      tp_size: degree of tensor-parallelism
      max_tokens: the maximum number of tokens to generate
      enforce_eager
      num_scheduler_steps: for multi-step scheduling, GPU-side steps per
                           GPU -> CPU output transfer
      num_prompts: number of example prompts under test
      num_logprobs: corresponds to the `logprobs` argument to the OpenAI
                    completions endpoint; `None` -> no logprobs
    """

    prompts = example_prompts
    if len(prompts) < num_prompts:
        prompts = prompts * ((num_prompts // len(prompts)) + 1)
    prompts = prompts[:num_prompts]
    assert len(prompts) == num_prompts

    with aphrodite_runner(
            model,
            dtype=dtype,
            enforce_eager=enforce_eager,
            gpu_memory_utilization=0.7,
            tensor_parallel_size=tp_size,
            use_v2_block_manager=True,
            num_scheduler_steps=num_scheduler_steps,
    ) as aphrodite_model:
        aphrodite_outputs = (aphrodite_model.generate_greedy(
            prompts, max_tokens)
                        if num_logprobs is None else
                        aphrodite_model.generate_greedy_logprobs(
                            prompts, max_tokens, num_logprobs))

    with hf_runner(model, dtype=dtype) as hf_model:
        hf_outputs = (hf_model.generate_greedy(prompts, max_tokens)
                      if num_logprobs is None else
                      hf_model.generate_greedy_logprobs_limit(
                          prompts, max_tokens, num_logprobs))

    if num_logprobs is None:
        check_outputs_equal(
            outputs_0_lst=hf_outputs,
            outputs_1_lst=aphrodite_outputs,
            name_0="hf",
            name_1="aphrodite",
        )
    else:
        check_logprobs_close(
            outputs_0_lst=hf_outputs,
            outputs_1_lst=aphrodite_outputs,
            name_0="hf",
            name_1="aphrodite",
        )


@pytest.mark.parametrize("model", MODELS)
@pytest.mark.parametrize("dtype", ["half"])
@pytest.mark.parametrize("tp_size", [1])
@pytest.mark.parametrize("max_tokens", [5])
@pytest.mark.parametrize("enforce_eager", [True])
@pytest.mark.parametrize("num_scheduler_steps", NUM_SCHEDULER_STEPS)
@pytest.mark.parametrize("num_prompts", NUM_PROMPTS)
@pytest.mark.parametrize("num_logprobs,num_prompt_logprobs", [(5, 5)])
def test_multi_step_llm_w_prompt_logprobs(
    aphrodite_runner,
    example_prompts,
    model: str,
    dtype: str,
    tp_size: int,
    max_tokens: int,
    enforce_eager: int,
    num_scheduler_steps: int,
    num_prompts: int,
    num_logprobs: Optional[int],
    num_prompt_logprobs: Optional[int],
) -> None:
    """Test prompt logprobs with multi-step scheduling via sync LLM Engine.
    Set up a Aphrodite engine instance w/ single-step scheduling as a
    ground-truth reference.
    Prompt them with the same example prompts.
    Validate:
    * All generated logprobs are all very close
    Args:
      hf_runner: HF transformers model runner fixture
      aphrodite_runner: Aphrodite model runner fixture
      example_prompts: test fixture providing example prompts
      model: model under test (same for single- and multi-step engines)
      dtype: tensor datatype for engine to utilize
      tp_size: degree of tensor-parallelism
      max_tokens: the maximum number of tokens to generate
      enforce_eager
      num_scheduler_steps: for multi-step scheduling, GPU-side steps per
                           GPU -> CPU output transfer
      num_prompts: number of example prompts under test
      num_logprobs: corresponds to the `logprobs` argument to the OpenAI
                    completions endpoint; `None` -> no logprobs
      num_prompt_logprobs: number of logprobs to return for each prompt token;
                           note that this argument is not supported by the
                           OpenAI completions endpoint.
    """
    prompts = example_prompts
    if len(prompts) < num_prompts:
        prompts = prompts * ((num_prompts // len(prompts)) + 1)
    prompts = prompts[:num_prompts]
    assert len(prompts) == num_prompts
    with aphrodite_runner(
            model,
            dtype=dtype,
            enforce_eager=enforce_eager,
            gpu_memory_utilization=0.7,
            tensor_parallel_size=tp_size,
            use_v2_block_manager=True,
            num_scheduler_steps=num_scheduler_steps,
    ) as aphrodite_model:
        aphrodite_outputs = aphrodite_model.generate_greedy_logprobs(
            prompts,
            max_tokens,
            num_logprobs,
            num_prompt_logprobs=num_prompt_logprobs)
    with aphrodite_runner(
            model,
            dtype=dtype,
            enforce_eager=enforce_eager,
            gpu_memory_utilization=0.7,
            tensor_parallel_size=tp_size,
    ) as aphrodite_model:
        single_step_aphrodite_outputs = (
            aphrodite_model.generate_greedy_logprobs(
                prompts,
                max_tokens,
                num_logprobs,
                num_prompt_logprobs=num_prompt_logprobs))
    check_logprobs_close(
        outputs_0_lst=single_step_aphrodite_outputs,
        outputs_1_lst=aphrodite_outputs,
        name_0="hf",
        name_1="aphrodite",
    )
