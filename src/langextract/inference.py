# Copyright 2025 Google LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Simple library for performing language model inference."""

import abc
from collections.abc import Iterator, Sequence
import dataclasses
import enum
import json
import textwrap
from typing import Any

from absl import logging
from typing_extensions import deprecated
import yaml

from . import data
from . import exceptions
from . import schema

_OLLAMA_DEFAULT_MODEL_URL = 'http://localhost:11434'


@dataclasses.dataclass(frozen=True)
class ScoredOutput:
  """Scored output."""

  score: float | None = None
  output: str | None = None

  def __str__(self) -> str:
    score_str = '-' if self.score is None else f'{self.score:.2f}'
    if self.output is None:
      return f'Score: {score_str}\nOutput: None'
    formatted_lines = textwrap.indent(self.output, prefix='  ')
    return f'Score: {score_str}\nOutput:\n{formatted_lines}'


class InferenceOutputError(exceptions.LangExtractError):
  """Exception raised when no scored outputs are available from the language model."""

  def __init__(self, message: str):
    self.message = message
    super().__init__(self.message)


class BaseLanguageModel(abc.ABC):
  """An abstract inference class for managing LLM inference.

  Attributes:
    _constraint: A `Constraint` object specifying constraints for model output.
  """

  def __init__(self, constraint: schema.Constraint = schema.Constraint()):
    """Initializes the BaseLanguageModel with an optional constraint.

    Args:
      constraint: Applies constraints when decoding the output. Defaults to no
        constraint.
    """
    self._constraint = constraint

  @abc.abstractmethod
  def infer(
      self, batch_prompts: Sequence[str], **kwargs
  ) -> Iterator[Sequence[ScoredOutput]]:
    """Implements language model inference.

    Args:
      batch_prompts: Batch of inputs for inference. Single element list can be
        used for a single input.
      **kwargs: Additional arguments for inference, like temperature and
        max_decode_steps.

    Returns: Batch of Sequence of probable output text outputs, sorted by
      descending
      score.
    """

  def infer_batch(
      self, prompts: Sequence[str], batch_size: int = 32  # pylint: disable=unused-argument
  ) -> list[list[ScoredOutput]]:
    """Batch inference with configurable batch size.

    This is a convenience method that collects all results from infer().

    Args:
      prompts: List of prompts to process.
      batch_size: Batch size (currently unused, for future optimization).

    Returns:
      List of lists of ScoredOutput objects.
    """
    results = []
    for output in self.infer(prompts):
      results.append(list(output))
    return results

  def parse_output(self, output: str) -> Any:
    """Parses model output as JSON or YAML.

    Note: This expects raw JSON/YAML without code fences.
    Code fence extraction is handled by resolver.py.

    Args:
      output: Raw output string from the model.

    Returns:
      Parsed Python object (dict or list).

    Raises:
      ValueError: If output cannot be parsed as JSON or YAML.
    """
    # Check if we have a format_type attribute (providers should set this)
    format_type = getattr(self, 'format_type', data.FormatType.JSON)

    try:
      if format_type == data.FormatType.JSON:
        return json.loads(output)
      else:
        return yaml.safe_load(output)
    except Exception as e:
      raise ValueError(
          f'Failed to parse output as {format_type.name}: {str(e)}'
      ) from e


class InferenceType(enum.Enum):
  ITERATIVE = 'iterative'
  MULTIPROCESS = 'multiprocess'


