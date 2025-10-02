from .cli import Config, run


def main() -> None:
    cfg = Config.from_args()
    run(cfg)


if __name__ == "__main__":
    main()
