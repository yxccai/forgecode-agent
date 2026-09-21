from v2.cli import main as stateful_main
from v3.agent import Runtime
from v3.tools import Tools


def main():
    stateful_main(Runtime, Tools, "V3")


if __name__ == "__main__":
    main()
