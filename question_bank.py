"""졸업시험 문제은행: GUI 학습, CLI 연습, 진도 저장 (표준 라이브러리만 사용)."""

from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_BANK = ROOT / "question_bank.json"
DEFAULT_PROGRESS = ROOT / "progress.json"


def load_bank(path: Path) -> tuple[dict, list[dict]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    questions = data.get("questions")
    if not isinstance(questions, list) or not questions:
        raise ValueError("문제 목록이 비어 있습니다.")
    ids = set()
    required = {"id", "section", "topic", "kind", "source", "question", "answer"}
    for question in questions:
        if not isinstance(question, dict) or not required <= question.keys():
            raise ValueError("문항 필드가 누락되었습니다.")
        if not all(isinstance(question[key], str) and question[key].strip() for key in required):
            raise ValueError(f"빈 문항 필드: {question.get('id', '?')}")
        if question["id"] in ids:
            raise ValueError(f"중복 문항 ID: {question['id']}")
        ids.add(question["id"])
    return data, questions


def filter_questions(questions: list[dict], section: str = "전체", kind: str = "전체", search: str = "") -> list[dict]:
    key = search.casefold().strip()
    return [q for q in questions
            if (section == "전체" or q["section"] == section)
            and (kind == "전체" or q["kind"] == kind)
            and (not key or key in " ".join((q["id"], q["topic"], q["question"], q["answer"])).casefold())]


def load_progress(path: Path) -> dict:
    if not path.exists():
        return {"version": 1, "records": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != 1 or not isinstance(data.get("records"), list):
        raise ValueError("진도 파일 형식이 올바르지 않습니다.")
    return data


def record_grade(progress: dict, path: Path, question_id: str, grade: int) -> None:
    if grade not in (0, 1, 2):
        raise ValueError("점수는 0, 1, 2 중 하나여야 합니다.")
    progress["records"].append({"id": question_id, "grade": grade, "at": datetime.now().astimezone().isoformat(timespec="seconds")})
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(progress, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def stats_text(progress: dict, questions: list[dict]) -> str:
    known = {q["id"] for q in questions}
    records = [r for r in progress["records"] if r.get("id") in known and r.get("grade") in (0, 1, 2)]
    latest = {r["id"]: r["grade"] for r in records}
    reviewed = len(latest)
    mastered = sum(v == 2 for v in latest.values())
    return f"학습 {reviewed}/{len(questions)}문항  |  최근 평가 2점 {mastered}문항  |  총 응답 {len(records)}회"


def cli_quiz(questions: list[dict], all_questions: list[dict], progress: dict, progress_path: Path, count: int, seed: int | None) -> None:
    if count < 1:
        raise ValueError("문항 수는 1 이상이어야 합니다.")
    draw = random.Random(seed).sample(questions, min(count, len(questions)))
    for index, q in enumerate(draw, 1):
        print(f"\n[{index}/{len(draw)}] {q['id']} · {q['topic']} · {q['kind']}")
        print(q["question"])
        try:
            input("답을 생각하거나 적은 뒤 Enter를 누르세요...")
            print(f"\n모범답안:\n{q['answer']}\n")
            while True:
                score = input("자가 채점 (0=다시, 1=부분, 2=정확 / Enter=건너뛰기): ").strip()
                if not score:
                    break
                if score in {"0", "1", "2"}:
                    record_grade(progress, progress_path, q["id"], int(score))
                    break
                print("0, 1, 2 또는 Enter를 입력하세요.")
        except (EOFError, KeyboardInterrupt):
            print("\n연습을 종료합니다.")
            break
    print(stats_text(progress, all_questions))


def launch_gui(bank: dict, questions: list[dict], progress: dict, progress_path: Path) -> None:
    import tkinter as tk
    from tkinter import ttk, messagebox
    from tkinter.scrolledtext import ScrolledText

    root = tk.Tk()
    root.title(bank.get("title", "문제은행"))
    root.geometry("1120x720")
    root.minsize(820, 560)
    root.configure(bg="#f4f7fb")
    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")
    style.configure("Treeview", rowheight=28, font=("맑은 고딕", 10))
    style.configure("Treeview.Heading", font=("맑은 고딕", 10, "bold"))
    style.configure("TButton", font=("맑은 고딕", 10), padding=6)
    style.configure("TLabel", font=("맑은 고딕", 10), background="#f4f7fb")

    section_var = tk.StringVar(value="전체")
    kind_var = tk.StringVar(value="전체")
    search_var = tk.StringVar()
    count_var = tk.IntVar(value=10)
    status_var = tk.StringVar()
    quiz: list[dict] = []
    quiz_index = -1
    current: dict | None = None
    revealed = False

    header = ttk.Frame(root, padding=(16, 14))
    header.pack(fill="x")
    ttk.Label(header, text="졸업시험 문제은행", font=("맑은 고딕", 18, "bold")).pack(side="left")
    ttk.Label(header, text=f"{len(questions)}문항 · 12개 주제", foreground="#4a647e").pack(side="right")

    controls = ttk.Frame(root, padding=(16, 4))
    controls.pack(fill="x")
    ttk.Label(controls, text="영역").pack(side="left")
    sections = ["전체"] + list(dict.fromkeys(q["section"] for q in questions))
    ttk.Combobox(controls, textvariable=section_var, values=sections, state="readonly", width=26).pack(side="left", padx=(5, 12))
    ttk.Label(controls, text="유형").pack(side="left")
    ttk.Combobox(controls, textvariable=kind_var, values=["전체", "핵심", "응용"], state="readonly", width=8).pack(side="left", padx=(5, 12))
    ttk.Label(controls, text="검색").pack(side="left")
    ttk.Entry(controls, textvariable=search_var, width=30).pack(side="left", padx=(5, 12), fill="x", expand=True)
    ttk.Label(controls, text="출제 수").pack(side="left")
    ttk.Spinbox(controls, from_=1, to=len(questions), textvariable=count_var, width=5).pack(side="left", padx=(5, 0))

    main = ttk.PanedWindow(root, orient="horizontal")
    main.pack(fill="both", expand=True, padx=16, pady=10)
    left = ttk.Frame(main)
    right = ttk.Frame(main)
    main.add(left, weight=1)
    main.add(right, weight=2)
    tree = ttk.Treeview(left, columns=("id", "topic", "kind"), show="headings", selectmode="browse")
    for key, label, width in (("id", "번호", 65), ("topic", "주제", 180), ("kind", "유형", 58)):
        tree.heading(key, text=label)
        tree.column(key, width=width, minwidth=50, stretch=key == "topic")
    tree.pack(side="left", fill="both", expand=True)
    scroll = ttk.Scrollbar(left, command=tree.yview)
    scroll.pack(side="right", fill="y")
    tree.configure(yscrollcommand=scroll.set)

    title = ttk.Label(right, text="문항을 선택하거나 무작위 출제를 시작하세요.", font=("맑은 고딕", 14, "bold"), wraplength=620)
    title.pack(anchor="w", pady=(2, 8))
    source = ttk.Label(right, text="", foreground="#607082")
    source.pack(anchor="w", pady=(0, 10))
    body = ScrolledText(right, wrap="word", font=("맑은 고딕", 12), padx=12, pady=12, state="disabled", height=10)
    body.pack(fill="both", expand=True)
    body.tag_configure("head", foreground="#286aa6", font=("맑은 고딕", 11, "bold"), spacing1=14)
    buttons = ttk.Frame(right, padding=(0, 10))
    buttons.pack(fill="x")

    def display(q: dict, show_answer: bool = False) -> None:
        nonlocal current, revealed
        current = q
        revealed = show_answer
        title.configure(text=f"{q['id']}  {q['topic']}  ·  {q['kind']}")
        source.configure(text=f"{q['section']}  |  {q['source']}")
        body.configure(state="normal")
        body.delete("1.0", "end")
        body.insert("end", "문제\n", "head")
        body.insert("end", q["question"] + "\n")
        if show_answer:
            body.insert("end", "\n모범답안\n", "head")
            body.insert("end", q["answer"])
        body.configure(state="disabled")
        body.yview_moveto(0)
        active = bool(quiz and 0 <= quiz_index < len(quiz) and q["id"] == quiz[quiz_index]["id"])
        for button in grade_buttons:
            button.configure(state="normal" if active and show_answer else "disabled")

    def filtered() -> list[dict]:
        return filter_questions(questions, section_var.get(), kind_var.get(), search_var.get())

    def refresh(*_args) -> None:
        selected = tree.selection()
        previous = selected[0] if selected else None
        tree.delete(*tree.get_children())
        for q in filtered():
            tree.insert("", "end", iid=q["id"], values=(q["id"], q["topic"], q["kind"]))
        if previous and tree.exists(previous):
            tree.selection_set(previous)
        status_var.set(f"검색 결과 {len(tree.get_children())}문항  |  {stats_text(progress, questions)}")

    def select_question(_event=None) -> None:
        if tree.selection():
            q = next(q for q in questions if q["id"] == tree.selection()[0])
            display(q)

    def reveal() -> None:
        if current:
            display(current, True)

    def draw() -> None:
        nonlocal quiz, quiz_index
        pool = filtered()
        if not pool:
            messagebox.showinfo("출제할 문항 없음", "검색 조건을 바꿔 주세요.")
            return
        try:
            n = max(1, int(count_var.get()))
        except (ValueError, tk.TclError):
            n = 10
        quiz = random.sample(pool, min(n, len(pool)))
        quiz_index = 0
        display(quiz[0])
        status_var.set(f"무작위 연습 1/{len(quiz)}  |  답안을 확인한 뒤 자가 채점하세요.")

    def next_question() -> None:
        nonlocal quiz_index, quiz
        if not quiz:
            draw()
            return
        quiz_index += 1
        if quiz_index >= len(quiz):
            quiz = []
            quiz_index = -1
            for button in grade_buttons:
                button.configure(state="disabled")
            status_var.set("연습 완료  |  " + stats_text(progress, questions))
            messagebox.showinfo("연습 완료", stats_text(progress, questions))
            return
        display(quiz[quiz_index])
        status_var.set(f"무작위 연습 {quiz_index + 1}/{len(quiz)}  |  답안을 확인한 뒤 자가 채점하세요.")

    def grade(score: int) -> None:
        if not current or not quiz or not revealed or current["id"] != quiz[quiz_index]["id"]:
            return
        record_grade(progress, progress_path, current["id"], score)
        next_question()

    ttk.Button(buttons, text="무작위 출제", command=draw).pack(side="left", padx=(0, 7))
    ttk.Button(buttons, text="정답 보기", command=reveal).pack(side="left", padx=(0, 7))
    ttk.Button(buttons, text="다음 문제", command=next_question).pack(side="left", padx=(0, 18))
    grade_buttons = []
    for text, score in (("0점 · 다시", 0), ("1점 · 부분", 1), ("2점 · 정확", 2)):
        button = ttk.Button(buttons, text=text, command=lambda value=score: grade(value), state="disabled")
        button.pack(side="left", padx=(0, 5))
        grade_buttons.append(button)

    ttk.Label(root, textvariable=status_var, padding=(16, 4), foreground="#4a647e").pack(fill="x")
    tree.bind("<<TreeviewSelect>>", select_question)
    for variable in (section_var, kind_var, search_var):
        variable.trace_add("write", refresh)
    refresh()
    root.mainloop()


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="졸업시험 문제은행 (기본 실행: GUI)")
    parser.add_argument("--bank", type=Path, default=DEFAULT_BANK, help="문제은행 JSON 파일")
    parser.add_argument("--progress", type=Path, default=DEFAULT_PROGRESS, help="진도 저장 JSON 파일")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("check", help="문항 데이터 검증")
    sub.add_parser("stats", help="학습 현황")
    listing = sub.add_parser("list", help="문항 목록")
    listing.add_argument("--section", default="전체")
    listing.add_argument("--kind", choices=["전체", "핵심", "응용"], default="전체")
    listing.add_argument("--search", default="")
    practice = sub.add_parser("quiz", help="터미널에서 무작위 연습")
    practice.add_argument("--section", default="전체")
    practice.add_argument("--kind", choices=["전체", "핵심", "응용"], default="전체")
    practice.add_argument("--search", default="")
    practice.add_argument("--count", type=int, default=10)
    practice.add_argument("--seed", type=int)
    args = parser.parse_args(argv)
    try:
        bank, questions = load_bank(args.bank)
        if args.command == "check":
            print(f"정상: {len(questions)}문항, {len(set(q['topic'] for q in questions))}개 주제, ID 중복 없음")
            return 0
        progress = load_progress(args.progress)
        if args.command == "stats":
            print(stats_text(progress, questions))
        elif args.command in {"list", "quiz"}:
            pool = filter_questions(questions, args.section, args.kind, args.search)
            if args.command == "list":
                for q in pool:
                    print(f"{q['id']}  [{q['kind']}] {q['section']} / {q['topic']} - {q['question']}")
                print(f"총 {len(pool)}문항")
            elif not pool:
                print("해당 조건의 문항이 없습니다.", file=sys.stderr)
                return 1
            else:
                cli_quiz(pool, questions, progress, args.progress, args.count, args.seed)
        else:
            launch_gui(bank, questions, progress, args.progress)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
