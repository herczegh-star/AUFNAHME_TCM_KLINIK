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
    results = matcher.find_best_templates(query, top_k=3)

    print("\nTop matches:\n")
    for i, t in enumerate(results, 1):
        print(f"{i}.")
        print(f"Section: {t.section}")
        print(f"Title:   {t.title}")
        print(f"Text:\n{t.text}")
        print()


if __name__ == "__main__":
    main()
