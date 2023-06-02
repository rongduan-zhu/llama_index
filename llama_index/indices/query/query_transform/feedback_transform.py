from typing import Dict, Optional

from llama_index.evaluation.base import Evaluation
from llama_index.indices.query.query_transform.base import BaseQueryTransform
from llama_index.indices.query.schema import QueryBundle
from llama_index.langchain_helpers.chain_wrapper import LLMPredictor
from llama_index.llm_predictor.base import BaseLLMPredictor
from llama_index.prompts.base import Prompt
from llama_index.response.schema import Response

DEFAULT_RESYNTHESIS_PROMPT_TMPL = (
    "Here is the original query:\n"
    "{query_str}\n"
    "Here is the response given:\n"
    "{response}\n"
    "Here is some feedback from evaluator about the response given.\n"
    "{feedback}\n"
    "If you want to resynthesize the query, please return the modified query below.\n"
    "Otherwise, please return the original query.\n"
)

DEFAULT_RESYNTHESIS_PROMPT = Prompt(DEFAULT_RESYNTHESIS_PROMPT_TMPL)


class FeedbackQueryTransformation(BaseQueryTransform):
    """Transform the query given the evaluation feedback.

    Args:
        eval(Evaluation): An evaluation object.
        resynthesize_query(bool): Whether to resynthesize the query.

    """

    def __init__(
        self,
        evaluation: Evaluation,
        llm_predictor: Optional[BaseLLMPredictor] = None,
        resynthesize_query: bool = False,
        resynthesis_prompt: Optional[Prompt] = None,
    ) -> None:
        super().__init__()
        self.evaluation = evaluation
        self.llm_predictor = llm_predictor or LLMPredictor()
        self.should_resynthesize_query = resynthesize_query
        self.resynthesis_prompt = resynthesis_prompt or DEFAULT_RESYNTHESIS_PROMPT

    def _run(self, query_bundle: QueryBundle, extra_info: Dict) -> QueryBundle:
        query_str = query_bundle.query_str
        if self.should_resynthesize_query:
            resynthesized_query = self.resynthesize_query(
                query_str, self.evaluation.response, self.evaluation.feedback
            )
        else:
            resynthesized_query = query_str
        new_query = (
            self.construct_feedback(response=self.evaluation.response.response)
            + "\n"
            + "Here is some feedback from the evaluator about the response given.\n"
            + self.evaluation.feedback
            + "\n"
            + "Now answer the question.\n"
            + resynthesized_query
        )
        return QueryBundle(new_query)

    def construct_feedback(self, response: Optional[str]) -> str:
        """Construct feedback from response."""
        if response is None:
            return ""
        else:
            return "Here is the previous answer.\n" + response

    def resynthesize_query(
        self, query_str: str, response: Response, feedback: Optional[str]
    ) -> str:
        """Resynthesize query given feedback."""
        if feedback is None:
            return query_str
        else:
            new_query_str, _ = self.llm_predictor.predict(
                self.resynthesis_prompt,
                query_str=query_str,
                response=response.response,
                feedback=feedback,
            )
            return new_query_str
