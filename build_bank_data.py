"""Export the edited workbook questions into a standalone JSON question bank."""

import ast
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
tree = ast.parse((ROOT / "make_workbook.py").read_text(encoding="utf-8"))
values = {}
for node in tree.body:
    if isinstance(node, ast.Assign) and len(node.targets) == 1:
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id in {"units", "answers"}:
            values[target.id] = ast.literal_eval(node.value)

if set(values) != {"units", "answers"}:
    raise RuntimeError("워크북에서 문항 또는 해설을 찾지 못했습니다.")

answers = {number: (a, b) for number, a, b in values["answers"]}
renumber = {"06": "11", "07": "12", "11": "06", "12": "07"}
questions = []
for section, entries in values["units"]:
    for number, topic, source, question_a, question_b in entries:
        if number not in answers:
            raise RuntimeError(f"{number}번 해설이 없습니다.")
        display_number = renumber.get(number, number)
        for variant, question, answer in zip("AB", (question_a, question_b), answers[number]):
            questions.append({
                "id": f"{display_number}{variant}",
                "section": section.split(". ", 1)[-1],
                "topic": topic,
                "kind": "핵심" if variant == "A" else "응용",
                "source": source,
                "question": question,
                "answer": answer,
            })

questions.sort(key=lambda question: question["id"])

bank = {
    "title": "졸업시험 문제은행",
    "version": 1,
    "source": "졸업시험 드가자.pdf (5쪽, 12개 주제)",
    "note": "9번의 산업 통계는 원문에 출처·집계 기준이 없어 검증형 문항으로 구성함.",
    "questions": questions,
}
target = ROOT / "question_bank.json"
target.write_text(json.dumps(bank, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"{target}: {len(questions)}문항")
