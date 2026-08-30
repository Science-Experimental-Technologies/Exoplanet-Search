"""Include existing project images in the documentation without duplicate sources."""

from pathlib import Path

from mkdocs.structure.files import File


def on_files(files, config, **kwargs):
    repository = Path(__file__).resolve().parents[1]
    for relative_path in (
        "assets/sxs-banner.png",
        "reports/confusion_matrices.png",
        "reports/candidate_figures/rank_05_8300900-r1.png",
    ):
        if not (repository / relative_path).is_file():
            raise FileNotFoundError(relative_path)
        files.append(
            File(
                relative_path,
                src_dir=str(repository),
                dest_dir=config.site_dir,
                use_directory_urls=config.use_directory_urls,
            )
        )
    return files
