"""Offline sanity check for the QA wiring — no real Anthropic call."""

from __future__ import annotations

from dataclasses import dataclass

from lac_ai.generate import ask


@dataclass
class _Block:
    type: str
    text: str


@dataclass
class _Response:
    content: list[_Block]


class FakeMessages:
    def create(self, **kwargs):
        ctx = kwargs["messages"][0]["content"]
        # Pretend Claude answered grounded in the first doc it sees in the context.
        first_id = ctx.split("[", 1)[1].split("]", 1)[0]
        return _Response(
            content=[
                _Block(
                    type="text",
                    text=f"Per the context, this is a stub answer [{first_id}].",
                )
            ]
        )


class FakeAnthropic:
    def __init__(self) -> None:
        self.messages = FakeMessages()


def main() -> None:
    ans = ask("Who invented the C programming language?", client=FakeAnthropic())
    print("Q:", ans.question)
    print("A:", ans.text)
    print("Citations:", ans.citations)
    print("Top retrieved:")
    for h in ans.retrieved[:3]:
        print(f"  {h.score:.3f}  {h.doc_id}  ({h.title})")
    print("Model:", ans.model)


if __name__ == "__main__":
    main()
