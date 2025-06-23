"""Classify keywords into categories using Google Gemini API."""

import argparse
from pathlib import Path

import google.generativeai as genai
import yaml


class KeywordInferencer:
    """A class to perform keyword category inference using Google's Gemini models.

    This class supports inference from:
    - Web snippet data stored in a YAML file
    - Simple keyword-only input (fallback when YAML is not provided)

    The class loads the Gemini API key from a YAML configuration file and uses
    the Gemini 1.5 Flash model for content generation.
    """

    def __init__(self, keyfile: Path):
        """Initialize the KeywordInferencer with an API key file.

        Parameters
        ----------
        keyfile : Path
            Path to the YAML file containing the API key under ['gemini']['api_key'].
        """
        self.api_key = self._load_api_key(keyfile)
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel("models/gemini-1.5-flash")

    def _load_api_key(self, keyfile: Path) -> str:
        """Load the Gemini API key from a YAML configuration file.

        Parameters
        ----------
        keyfile : Path
            Path to the YAML file containing the API key.

        Returns:
        -------
        str
            The extracted API key string.
        """
        with open(keyfile, encoding="utf-8") as f:
            keys = yaml.safe_load(f)
        return keys["gemini"]["api_key"]

    def infer_from_yaml(self, yaml_path: Path, categories: list[str]) -> str:
        """Perform inference based on a YAML file.

        Parameters
        ----------
        yaml_path : Path
            Path to the YAML file with 'keyword' and 'results' fields.
        categories : list of str
            List of candidate category labels to choose from.

        Returns:
        -------
        str
            The inferred category name as a single word.
        """
        with open(yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        keyword = data["keyword"]
        snippets = [entry["snippet"] for entry in data["results"]]
        context = "\n".join(snippets[:3])  # Limit to the first 3 snippets

        prompt = (
            "You are an expert in industrial products.\n\n"
            f"Based on the web information below, "
            f"determine which of the following categories "
            f"best classifies the keyword '{keyword}'. Respond with only one word.\n\n"
            f"Category candidates: {', '.join(categories)}\n\n"
            f"Snippets:\n{context}"
        )

        response = self.model.generate_content(prompt)
        return response.text.strip()

    def infer_from_web(self, keyword: str, categories: list[str]) -> str:
        """Perform inference using only the keyword and category list (no web snippets).

        Parameters
        ----------
        keyword : str
            The keyword to classify.
        categories : list of str
            List of candidate category labels to choose from.

        Returns:
        -------
        str
            The inferred category name as a single word.
        """
        prompt = (
            "You are an expert in industrial products.\n\n"
            f"Based on your knowledge, determine which of the following categories "
            f"best classifies the keyword '{keyword}'. Respond with only one word.\n\n"
            f"Category candidates: {', '.join(categories)}"
        )

        response = self.model.generate_content(prompt)
        return response.text.strip()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Infer keyword category using Gemini")
    parser.add_argument(
        "--yaml", type=str, help="Path to YAML file (optional)", default=None
    )
    parser.add_argument(
        "--keyword", type=str, help="Keyword (used only if no YAML)", default=None
    )
    parser.add_argument(
        "--categories",
        type=str,
        nargs="+",
        required=True,
        help="List of category candidates",
    )
    parser.add_argument(
        "--keyfile",
        type=str,
        default="/home/tomo/git/vc_testing/keys.yaml",
        help="Path to keys.yaml",
    )
    args = parser.parse_args()

    inferencer = KeywordInferencer(Path(args.keyfile))

    if args.yaml:
        result = inferencer.infer_from_yaml(Path(args.yaml), args.categories)
    elif args.keyword:
        result = inferencer.infer_from_web(args.keyword, args.categories)
    else:
        raise ValueError("Either --yaml or --keyword must be provided.")

    print(result)
