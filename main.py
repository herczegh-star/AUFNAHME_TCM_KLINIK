from core.template_repository import TemplateRepository
from core.embedding_index import EmbeddingIndex
from core.template_matcher import TemplateMatcher


def main() -> None:
    print("Loading templates...")
    repo = TemplateRepository()
    repo.load_templates()

    print("Building embedding index...")
    index = EmbeddingIndex()
    index.build_index(repo.get_all_templates())

    matcher = TemplateMatcher(repo, index)

    print("\nTemplate selection ready.\n")

    query = input("User input:\n> ").strip()
    result = matcher.find_best_template(query)

    print("\nBest template:")
    print(f"Section: {result.section}")
    print(f"Title:   {result.title}")
    print(f"Text:\n{result.text}")


if __name__ == "__main__":
    main()
