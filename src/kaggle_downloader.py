from typing import Callable, Union
from kaggle import KaggleApi

from kaggle.models.kaggle_models_extended import Kernel, Competition


class KaggleDownloader:
    def __init__(self) -> None:
        self.client = KaggleApi()
        self.client.authenticate()

    def fetch_competition_refs(self) -> list[str]:
        return self._fetch_all_pages(
            lambda page: self.client.competitions_list(page=page)
        )

    def fetch_kernel_refs(self, competition_ref: str) -> list[str]:
        return self._fetch_all_pages(
            lambda page: self.client.kernels_list(
                competition=competition_ref,
                page=page,
                page_size=100
            )
        )

    def fetch_notebook(self, kernel_ref: str) -> dict:
        user_name, kernel_slug = kernel_ref.split("/")
        return self.client.kernel_pull(user_name, kernel_slug)

    @staticmethod
    def _fetch_all_pages(fetcher: Callable[[int], list[Union[Kernel, Competition]]]) -> list[str]:
        result = []
        page = 1

        while True:
            # noinspection PyUnresolvedReferences
            batch = [it.ref for it in fetcher(page)]

            if len(batch) == 0:
                break

            result += batch
            page += 1

        return result
