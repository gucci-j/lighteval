# MIT License

# Copyright (c) 2024 The HuggingFace Team

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from contextlib import nullcontext

import torch
from transformers import AutoModelForCausalLM, PreTrainedTokenizer

from lighteval.logging.hierarchical_logger import hlog
from lighteval.models.base_model import BaseModel
from lighteval.models.model_config import AdapterModelConfig, EnvConfig
from lighteval.models.utils import _get_dtype
from lighteval.utils import is_peft_available


if is_peft_available():
    from peft import PeftModel, PeftModelForCausalLM


class AdapterModel(BaseModel):
    def _create_auto_tokenizer(self, config: AdapterModelConfig, env_config: EnvConfig) -> PreTrainedTokenizer:
        # By default, we look at the model config for the model stored in `base_model`
        # (= the parent model, not the model of interest)
        return self._create_auto_tokenizer_with_name(config.base_model, config=config, env_config=env_config)

    def _create_auto_model(self, config: AdapterModelConfig, env_config: EnvConfig) -> AutoModelForCausalLM:
        """Returns a PeftModel from a base model and a version fined tuned using PEFT."""
        torch_dtype = _get_dtype(config.dtype, self._config)
        config.model_parallel, max_memory, device_map = self.init_model_parallel(config.model_parallel)
        adapter_weights = config.pretrained
        hlog(f"Loading model from {adapter_weights} and applying adapter to {config.base_model}")
        base = AutoModelForCausalLM.from_pretrained(
            config.base_model,  
            low_cpu_mem_usage=True, 
            max_memory=max_memory,
            device_map=device_map,
            torch_dtype=torch.float16 if torch_dtype in (torch.float64, torch.float32) else torch_dtype,
            trust_remote_code=config.trust_remote_code,
            cache_dir=env_config.cache_dir,
            quantization_config=config.quantization_config,
            token=env_config.token,
        )
        model = PeftModelForCausalLM.from_pretrained(base, adapter_weights)
        
        return model
        