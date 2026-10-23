#!/usr/bin/env python3
"""Audit EXPECT records and the SVA/VFORM/NNUM 1-to-1 subset.

Python 3.9+; standard library only. No model training, prediction or scoring.
Original data convention (read_jsonl.py): target + [MOD] + source.
The input files are never changed. Test is not read unless explicitly enabled.
"""

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from zipfile import ZipFile


NONE = "[NONE]"
TYPE_MAP = {
    "Subject-Verb Agreement": "SVA",
    "Infinitives": "VFORM",
    "Gerund": "VFORM",
    "Participle": "VFORM",
    "Number": "NNUM",
}
LABELS = ("SVA", "VFORM", "NNUM")


def json_text(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def write_csv(path, rows):
    if not rows:
        # An empty JSON array is also written where an empty detailed table matters.
        path.write_text("no_rows\n", encoding="utf-8-sig")
        return
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def load_records(text):
    """Return (record number, original file line or None, JSON object)."""
    if text.lstrip().startswith("["):
        rows = json.loads(text)
        if not isinstance(rows, list):
            raise ValueError("Expected a JSON array or JSONL file.")
        return [(i, None, row) for i, row in enumerate(rows, 1)]
    rows = []
    for line_no, line in enumerate(text.splitlines(), 1):
        if line.strip():
            rows.append((len(rows) + 1, line_no, json.loads(line)))
    return rows


def decode_record(raw, split, number, file_line=None):
    """Decode gold coordinates, then project visible SOURCE tokens to labels.

    Left half of correction_index indexes TARGET. Right half indexes SOURCE
    after subtracting len(TARGET)+1. Using len(source) here is incorrect when
    the two lengths differ. [NONE] is an alignment placeholder, not a word.
    """
    record_id = "{}:{:06d}".format(split, number)
    for field in ("source", "target", "correction_index", "error_type"):
        if field not in raw:
            raise ValueError("{}: missing {}".format(record_id, field))
    source, target = raw["source"], raw["target"]
    indices = raw["correction_index"]
    if not all(isinstance(x, list) for x in (source, target, indices)):
        raise ValueError("{}: token arrays and correction_index must be lists".format(record_id))
    if not all(isinstance(x, str) for x in source + target):
        raise ValueError("{}: non-string token".format(record_id))
    nt, ns = len(target), len(source)
    if not all(type(i) is int and 0 <= i < nt + 1 + ns for i in indices):
        raise ValueError("{}: invalid concatenated correction index".format(record_id))
    if len(indices) != len(set(indices)) or nt in indices:
        raise ValueError("{}: duplicate index or separator selected as correction".format(record_id))
    target_positions = sorted(i for i in indices if i < nt)
    source_positions = sorted(i - nt - 1 for i in indices if i > nt)
    if not source_positions or not target_positions:
        raise ValueError("{}: an edit needs indices on both sides, including [NONE] for a gap".format(record_id))

    clean_tokens, raw_to_clean, gap_at_raw = [], [], []
    for token in source:
        gap_at_raw.append(len(clean_tokens))
        if token == NONE:
            raw_to_clean.append(None)
        else:
            raw_to_clean.append(len(clean_tokens))
            clean_tokens.append(token)
    source_span = [source[i] for i in source_positions]
    target_span = [target[i] for i in target_positions]
    source_real_positions = sorted(raw_to_clean[i] for i in source_positions if source[i] != NONE)
    source_gap_positions = sorted({gap_at_raw[i] for i in source_positions if source[i] == NONE})
    source_real_span = [word for word in source_span if word != NONE]
    target_real_span = [word for word in target_span if word != NONE]
    outside_source = [word for i, word in enumerate(source) if i not in source_positions and word != NONE]
    outside_target = [word for i, word in enumerate(target) if i not in target_positions and word != NONE]
    outside_equal = outside_source == outside_target
    if not outside_equal:
        raise ValueError("{}: source/target contexts outside the annotated edit differ".format(record_id))

    mapped_type = TYPE_MAP.get(raw["error_type"])
    strict_one_to_one = (
        len(source_positions) == len(target_positions) == 1
        and NONE not in source_span + target_span
        and source_span != target_span
    )
    if strict_one_to_one:
        edit_kind = "substitution_1_to_1"
    elif not source_real_span and target_real_span:
        edit_kind = "insertion"
    elif source_real_span and not target_real_span:
        edit_kind = "deletion"
    elif NONE in source_span + target_span:
        edit_kind = "mixed_placeholder_edit"
    elif source_real_span == target_real_span:
        edit_kind = "unchanged_or_empty_edit"
    else:
        edit_kind = "multi_token_replacement"
    retained = mapped_type is None or strict_one_to_one
    labels_before = ["O"] * len(clean_tokens)
    if mapped_type:
        for index in source_real_positions:
            labels_before[index] = mapped_type

    # Reproduce the OLD scripts exactly, only to expose differences in the audit.
    # This decoding must not be used as the corrected gold conversion.
    legacy_left = [i for i in indices if i < ns]
    legacy_right = [i - ns - 1 for i in indices if i > ns]
    legacy_valid = all(0 <= i < nt for i in legacy_right)
    legacy_source_span = [source[i] for i in legacy_left]
    legacy_target_span = [target[i] for i in legacy_right] if legacy_valid else []
    legacy_one_to_one = (
        legacy_valid and len(legacy_source_span) == len(legacy_target_span) == 1
        and NONE not in legacy_source_span + legacy_target_span
    )
    legacy_retained = mapped_type is None or legacy_one_to_one
    legacy_gold = []
    if mapped_type and legacy_retained:
        legacy_gold = [raw_to_clean[legacy_left[0]]]
        if legacy_gold[0] is None:
            raise ValueError("{}: legacy retained a placeholder".format(record_id))

    source_key = tuple(clean_tokens)
    # Identity is exact token text, not a document/sentence ID (none is supplied).
    source_id = hashlib.sha256(json_text(clean_tokens).encode("utf-8")).hexdigest()
    return {
        "record_id": record_id, "split": split, "record_number_1based": number,
        "file_line_1based": file_line, "raw": raw, "source_key": source_key,
        "source_text_id": source_id, "clean_source_tokens": clean_tokens,
        "raw_source_to_clean_index": raw_to_clean,
        "target_offset": 0, "source_offset": nt + 1,
        "target_positions_raw_0based": target_positions,
        "source_positions_raw_0based": source_positions,
        "source_positions_clean_0based": source_real_positions,
        "source_gap_positions_clean_0based": source_gap_positions,
        "source_edit_tokens": source_span, "target_edit_tokens": target_span,
        "mapped_type": mapped_type, "edit_kind": edit_kind,
        "strict_one_to_one": strict_one_to_one, "retained": retained,
        "outside_span_equal": outside_equal,
        "labels_before_filter_diagnostic": labels_before,
        "labels_after_filter": labels_before if retained else None,
        "legacy_retained": legacy_retained,
        "legacy_source_positions_clean_0based": legacy_gold,
        "legacy_source_edit_tokens": legacy_source_span,
        "legacy_target_edit_tokens": legacy_target_span,
    }


def event_signature(record):
    """Deduplicate an annotated EDIT, not its individual source token positions.

    Labels are deliberately not part of this signature. Different class labels
    at the same position are reported separately as conflicts, never resolved.
    """
    return (
        tuple(record["source_positions_clean_0based"]),
        tuple(record["source_gap_positions_clean_0based"]),
        tuple(x for x in record["target_edit_tokens"] if x != NONE),
    )


def grouped_sources(records):
    groups = defaultdict(list)
    for record in records:
        groups[record["source_key"]].append(record)
    return groups


def stage_statistics(split, stage, records):
    groups = grouped_sources(records)
    targets = [r for r in records if r["mapped_type"]]
    histograms = defaultdict(Counter)
    for record in records:
        target = bool(record["mapped_type"])
        histograms[("annotation_record", "target_annotated_edits")][int(target)] += 1
        histograms[("annotation_record", "target_real_source_positions")][
            len(record["source_positions_clean_0based"]) if target else 0] += 1
    union_positions = union_events = groups_with_events = groups_with_positions = 0
    multi_events = multi_positions = conflicts = 0
    duplicate_events = 0
    for group in groups.values():
        target_group = [r for r in group if r["mapped_type"]]
        positions = set()
        events = set()
        types_at_position = defaultdict(set)
        for record in target_group:
            events.add(event_signature(record))
            for index in record["source_positions_clean_0based"]:
                positions.add(index)
                types_at_position[index].add(record["mapped_type"])
        union_positions += len(positions)
        union_events += len(events)
        groups_with_events += bool(events)
        groups_with_positions += bool(positions)
        multi_events += len(events) >= 2
        multi_positions += len(positions) >= 2
        conflicts += sum(len(types) > 1 for types in types_at_position.values())
        duplicate_events += len(target_group) - len(events)
        histograms[("source_text_group", "target_annotated_edits")][len(events)] += 1
        histograms[("source_text_group", "target_real_source_positions")][len(positions)] += 1
    row = {
        "split": split, "stage": stage,
        "annotation_records": len(records), "unique_source_texts": len(groups),
        "duplicate_record_excess_by_source": len(records) - len(groups),
        "source_tokens_including_NONE_record_occurrences": sum(len(r["raw"]["source"]) for r in records),
        "NONE_placeholders_record_occurrences": sum(r["raw"]["source"].count(NONE) for r in records),
        "visible_source_tokens_record_occurrences": sum(len(r["clean_source_tokens"]) for r in records),
        "visible_source_tokens_once_per_source_text": sum(len(key) for key in groups),
        "all_annotated_edit_records": len(records),
        "target_annotated_edit_records": len(targets),
        "records_with_no_target_annotation": len(records) - len(targets),
        "target_records_with_zero_real_source_positions": sum(not r["source_positions_clean_0based"] for r in targets),
        "target_records_with_one_real_source_position": sum(len(r["source_positions_clean_0based"]) == 1 for r in targets),
        "target_records_with_ge2_real_source_positions": sum(len(r["source_positions_clean_0based"]) >= 2 for r in targets),
        "records_with_any_target_source_position": sum(bool(r["source_positions_clean_0based"]) for r in targets),
        "target_source_position_record_occurrences": sum(len(r["source_positions_clean_0based"]) for r in targets),
        "target_gap_position_record_occurrences": sum(len(r["source_gap_positions_clean_0based"]) for r in targets),
        "unique_source_texts_with_any_target_annotation": groups_with_events,
        "unique_source_texts_with_any_target_source_position": groups_with_positions,
        "target_source_positions_union_per_source_text": union_positions,
        "target_distinct_edit_events_per_source_text": union_events,
        "duplicate_target_edit_annotation_excess": duplicate_events,
        "source_texts_with_ge2_target_edits": multi_events,
        "source_texts_with_ge2_target_positions": multi_positions,
        "target_position_type_conflicts": conflicts,
        "unequal_source_target_length_records": sum(len(r["raw"]["source"]) != len(r["raw"]["target"]) for r in records),
        "outside_span_alignment_failures": sum(not r["outside_span_equal"] for r in records),
    }
    distribution = []
    for (unit, measure), counts in sorted(histograms.items()):
        for number in sorted(set(counts) | {0, 1, 2}):
            distribution.append({
                "split": split, "stage": stage, "unit": unit, "measure": measure,
                "number_of_annotated_edits_or_positions": number, "number_of_units": counts[number],
            })
    # Reconciliation checks independent of the display formatting.
    assert row["visible_source_tokens_record_occurrences"] + row["NONE_placeholders_record_occurrences"] == row["source_tokens_including_NONE_record_occurrences"]
    assert row["records_with_no_target_annotation"] + row["target_annotated_edit_records"] == len(records)
    assert sum(histograms[("annotation_record", "target_real_source_positions")].values()) == len(records)
    assert sum(k * v for k, v in histograms[("annotation_record", "target_real_source_positions")].items()) == row["target_source_position_record_occurrences"]
    assert sum(k * v for k, v in histograms[("source_text_group", "target_real_source_positions")].items()) == union_positions
    if stage == "after_filter":
        assert row["target_source_position_record_occurrences"] == len(targets)
        assert row["target_gap_position_record_occurrences"] == 0
        for record in targets:
            assert sum(label != "O" for label in record["labels_after_filter"]) == 1
    return row, distribution


def class_statistics(split, stage, records):
    rows = []
    for label in LABELS:
        selected = [r for r in records if r["mapped_type"] == label]
        rows.append({
            "split": split, "stage": stage, "mapped_type": label,
            "annotated_edit_records": len(selected),
            "visible_source_error_position_occurrences": sum(len(r["source_positions_clean_0based"]) for r in selected),
            "source_gap_occurrences": sum(len(r["source_gap_positions_clean_0based"]) for r in selected),
            "strict_one_to_one_records": sum(r["strict_one_to_one"] for r in selected),
            "unique_source_texts_with_type": len({r["source_key"] for r in selected}),
        })
    return rows


def audit_record_row(record):
    return {
        "split": record["split"], "record_id": record["record_id"],
        "record_number_1based": record["record_number_1based"],
        "file_line_1based": record["file_line_1based"],
        "source_text_id_sha256": record["source_text_id"],
        "original_error_type": record["raw"]["error_type"],
        "mapped_type": record["mapped_type"] or "OUTSIDE_3_TYPES",
        "retained": record["retained"], "edit_kind": record["edit_kind"],
        "source_raw_length": len(record["raw"]["source"]),
        "target_raw_length": len(record["raw"]["target"]),
        "source_offset_in_target_MOD_source": record["source_offset"],
        "correction_index_original_json": json_text(record["raw"]["correction_index"]),
        "source_positions_raw_0based_json": json_text(record["source_positions_raw_0based"]),
        "source_positions_clean_0based_json": json_text(record["source_positions_clean_0based"]),
        "source_gap_positions_clean_0based_json": json_text(record["source_gap_positions_clean_0based"]),
        "target_positions_raw_0based_json": json_text(record["target_positions_raw_0based"]),
        "source_edit_tokens_json": json_text(record["source_edit_tokens"]),
        "target_edit_tokens_json": json_text(record["target_edit_tokens"]),
        "clean_source_tokens_json": json_text(record["clean_source_tokens"]),
        "labels_before_filter_diagnostic_json": json_text(record["labels_before_filter_diagnostic"]),
        "labels_after_filter_json": json_text(record["labels_after_filter"]),
        "outside_span_equal": record["outside_span_equal"],
        "legacy_retained": record["legacy_retained"],
    }


def legacy_mismatch(record):
    return record["legacy_retained"] != record["retained"] or (
        record["mapped_type"] and record["retained"] and record["legacy_retained"]
        and record["source_positions_clean_0based"] != record["legacy_source_positions_clean_0based"]
    )


def choose_five_examples(records):
    """Deterministic: three supported labels, one other type, one excluded edit.

    No test examples. Prefer short dev examples; the excluded example prefers
    an actual legacy decoding mismatch to make the bug independently visible.
    """
    pool = [r for r in records if r["split"] != "test"]
    def rank(record):
        return (record["split"] != "dev", len(record["clean_source_tokens"]), record["record_id"])
    selected = []
    for label in LABELS:
        candidates = [r for r in pool if r["mapped_type"] == label and r["retained"]]
        if not candidates:
            raise ValueError("Need a retained {} example in train/dev.".format(label))
        selected.append(("Giữ mẫu thay thế 1-1: " + label, min(candidates, key=rank)))
    other = [r for r in pool if r["mapped_type"] is None]
    if not other:
        raise ValueError("Need one example outside the three target types.")
    selected.append(("Giữ bản ghi ngoài ba loại, nhãn mục tiêu toàn O", min(other, key=rank)))
    excluded = [r for r in pool if r["mapped_type"] and not r["retained"]]
    if not excluded:
        raise ValueError("Need one excluded target edit example.")
    mismatches = [r for r in excluded if legacy_mismatch(r)]
    many_to_one = [r for r in mismatches if len(r["source_positions_clean_0based"]) >= 2
                   and len([x for x in r["target_edit_tokens"] if x != NONE]) == 1]
    illustrative = many_to_one or mismatches
    fifth = min(illustrative, key=lambda r: (len(r["clean_source_tokens"]), r["record_id"])) if illustrative else min(excluded, key=rank)
    selected.append(("Loại mẫu không phải 1-1; không biến thành nhãn O", fifth))
    examples = []
    for number, (purpose, record) in enumerate(selected, 1):
        example = {k: v for k, v in record.items() if k != "source_key"}
        example["example_number"] = number
        example["purpose"] = purpose
        examples.append(example)
    return examples


def examples_markdown(examples):
    lines = [
        "# Năm ví dụ kiểm tra chuyển annotation sang token", "",
        "Ví dụ lấy trực tiếp từ JSON; giữ nguyên lỗi và cách token hóa gốc. Chỉ số token bắt đầu từ 0.",
        "`correction_index` đánh số trên `target + [MOD] + source`. Offset của source là `len(target) + 1`.",
        "Nhãn O chỉ có nghĩa là không được gán một trong ba nhãn mục tiêu ở bản ghi này; không chứng minh token đúng ngữ pháp.", "",
    ]
    for example in examples:
        raw = example["raw"]
        lines += ["## Ví dụ {} {}".format(example["example_number"], example["record_id"]), "",
                  example["purpose"], "",
                  "- Loại gốc: `{}`; nhãn gộp: `{}`.".format(raw["error_type"], example["mapped_type"] or "ngoài phạm vi"),
                  "- Độ dài target/source có placeholder: {}/{}; offset source: {}.".format(len(raw["target"]), len(raw["source"]), example["source_offset"]),
                  "- correction_index gốc: `{}`.".format(raw["correction_index"]),
                  "- Vị trí trong target: `{}`; trong source gốc: `{}`; source sau bỏ [NONE]: `{}`.".format(example["target_positions_raw_0based"], example["source_positions_raw_0based"], example["source_positions_clean_0based"]),
                  "- Span sửa: `{}` → `{}`.".format(" ".join(example["source_edit_tokens"]), " ".join(example["target_edit_tokens"])),
                  "- Quyết định: **{}**; dạng edit: `{}`.".format("GIỮ" if example["retained"] else "LOẠI", example["edit_kind"]), "",
                  "Source sau bỏ placeholder:", "", "```text", " ".join(example["clean_source_tokens"]), "```", "",
                  "Target gốc:", "", "```text", " ".join(raw["target"]), "```", "",
                  "| Chỉ số source gốc | Chỉ số source sạch | Token | Chiếu nhãn trước lọc | Nhãn dùng sau lọc |",
                  "| ---: | ---: | --- | --- | --- |"]
        for old_index, token in enumerate(raw["source"]):
            clean_index = example["raw_source_to_clean_index"][old_index]
            diagnostic = "placeholder, không phải token" if clean_index is None else example["labels_before_filter_diagnostic"][clean_index]
            final = "không có" if clean_index is None else (example["labels_after_filter"][clean_index] if example["retained"] else "không dùng, bản ghi bị loại")
            lines.append("| {} | {} | {} | {} | {} |".format(old_index, "—" if clean_index is None else clean_index, token.replace("|", "\\|"), diagnostic, final))
        lines += ["", "Vector nhãn sau lọc:", "", "```json", json.dumps(example["labels_after_filter"], ensure_ascii=False), "```", ""]
        if not example["retained"]:
            lines += ["`null` nghĩa là không đưa bản ghi vào benchmark 1-1, không phải đổi các token thành O.", ""]
        if legacy_mismatch(example):
            lines += ["Cách giải mã cũ giữ nhầm mẫu này: đọc source span `{}` và target span `{}`. Dùng offset đúng cho thấy đây là edit {}→{} token thật.".format(
                " ".join(example["legacy_source_edit_tokens"]), " ".join(example["legacy_target_edit_tokens"]),
                len(example["source_positions_clean_0based"]), len([x for x in example["target_edit_tokens"] if x != NONE])), ""]
        lines += ["Annotation JSON đầy đủ, gồm cả evidence và parsing, nằm trong `examples_5.json`.", ""]
    return "\n".join(lines)


def audit_report(summary, class_rows, exclusions, legacy_rows, examples, fingerprints):
    lines = [
        "# Kiểm đếm EXPECT và kiểm tra chuyển nhãn", "",
        "Bước 1 chỉ kiểm tra dữ liệu và đơn vị đếm. Không huấn luyện mô hình, không sinh dự đoán, không tính P/R/F và không thay đổi dữ liệu gốc.", "",
        "## Đơn vị phải phân biệt", "",
        "- Bản ghi annotation: một phần tử JSON, có một error_type và một edit được annotation. Không tự gọi mỗi bản ghi là một câu văn độc lập.",
        "- Chuỗi source duy nhất: nhóm theo toàn bộ dãy token source sau khi bỏ [NONE], giữ nguyên chữ hoa/thường. Đây là định danh theo văn bản vì không có ID câu/tài liệu; hai lần xuất hiện độc lập có cùng văn bản có thể bị gộp.",
        "- Token thật: token source khác [NONE]. Bảng tách token đếm theo lượt bản ghi và token đếm một lần mỗi chuỗi source.",
        "- Edit được annotation: một thao tác sửa có thể liên quan nhiều token hoặc chỉ một chỗ trống cần chèn. Hai token trong một span không tự động là hai lỗi ngữ pháp độc lập.",
        "- Vị trí lỗi: vị trí token thật trong source có annotation của ba loại mục tiêu. Chỗ chèn được đếm riêng là gap, không phải token lỗi.",
        "- Nhãn O: không có nhãn mục tiêu tại token đó trong bản ghi hiện tại; không đồng nghĩa với đúng ngữ pháp hoặc câu sạch.", "",
        "## Bảng trước và sau lọc", "",
        "| Split | Giai đoạn | Bản ghi | Chuỗi source duy nhất | Token thật theo lượt bản ghi | Edit ba loại | Vị trí token ba loại | Gap ba loại |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary:
        lines.append("| {} | {} | {} | {} | {} | {} | {} | {} |".format(
            row["split"], "trước lọc" if row["stage"] == "before_filter" else "sau lọc",
            row["annotation_records"], row["unique_source_texts"], row["visible_source_tokens_record_occurrences"],
            row["target_annotated_edit_records"], row["target_source_position_record_occurrences"], row["target_gap_position_record_occurrences"]))
    lines += ["", "Token thật khác số token có cả placeholder trong báo cáo cũ. Xem đầy đủ hai cách đếm trong `counts_summary.csv`.", "",
              "## Phân bố số lỗi mỗi đơn vị", "",
              "`error_count_distribution.csv` tách hai đơn vị: lượt bản ghi và nhóm chuỗi source; mỗi đơn vị có cả số edit và số vị trí token. Không dùng số vị trí token để thay thế số edit.", "",
              "| Split | Giai đoạn | Chuỗi source có 0 vị trí mục tiêu | Có 1 vị trí | Có ≥2 vị trí |",
              "| --- | --- | ---: | ---: | ---: |"]
    for row in summary:
        n_any = row["unique_source_texts_with_any_target_source_position"]
        n_multi = row["source_texts_with_ge2_target_positions"]
        lines.append("| {} | {} | {} | {} | {} |".format(row["split"],
            "trước lọc" if row["stage"] == "before_filter" else "sau lọc",
            row["unique_source_texts"] - n_any, n_any - n_multi, n_multi))
    lines += ["", "Một edit có thể gồm nhiều vị trí; bảng trên là số vị trí, không phải số lỗi độc lập. Bảng edit sau lọc:", "",
              "| Split sau lọc | Chuỗi source có ≥2 edit mục tiêu đã annotation | Chuỗi source có ≥2 vị trí mục tiêu | Vị trí có nhãn mục tiêu mâu thuẫn |",
              "| --- | ---: | ---: | ---: |"]
    for row in summary:
        if row["stage"] == "after_filter":
            lines.append("| {} | {} | {} | {} |".format(row["split"], row["source_texts_with_ge2_target_edits"], row["source_texts_with_ge2_target_positions"], row["target_position_type_conflicts"]))
    lines += ["", "Các số này chỉ mô tả annotation được quan sát. Không kết luận mỗi câu tự nhiên có tối đa một lỗi. Việc lọc có điều kiện trên gold đã đổi quần thể đánh giá.", ""]
    dev_after = next((row for row in summary if row["split"] == "dev" and row["stage"] == "after_filter"), None)
    if dev_after:
        lines += ["Trên dev sau lọc, {} bản ghi thuộc {} chuỗi source khác nhau. Đếm trực tiếp có {} bản ghi được annotation edit mục tiêu và {} bản ghi không có annotation của ba loại mục tiêu. Phép trừ cho đúng số trong trường hợp này sau khi đã kiểm tra số chuỗi trùng và số edit mỗi chuỗi; không mặc định coi số token lỗi là số câu có lỗi.".format(
            dev_after["annotation_records"], dev_after["unique_source_texts"],
            dev_after["target_annotated_edit_records"], dev_after["records_with_no_target_annotation"]), ""]
    lines += [
              "## Phạm vi và số mẫu bị loại", "",
              "Giữ bản ghi thuộc SVA/VFORM/NNUM chỉ khi span source và target đều đúng một token, không [NONE], có thay đổi. Bản ghi thuộc các loại khác được giữ với nhãn mục tiêu toàn O, giống thiết kế cũ. Chúng không phải tập câu sạch đã được chứng nhận.", "",
              "| Split | SVA sau lọc | VFORM sau lọc | NNUM sau lọc | Tổng sau lọc | Mẫu mục tiêu bị loại |",
              "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for split in fingerprints:
        counts = {r["mapped_type"]: r["annotated_edit_records"] for r in class_rows if r["split"] == split and r["stage"] == "after_filter"}
        dropped = sum(r["records"] for r in exclusions if r["split"] == split)
        lines.append("| {} | {} | {} | {} | {} | {} |".format(split, counts["SVA"], counts["VFORM"], counts["NNUM"], sum(counts.values()), dropped))
    lines += ["", "Loại nào và vì sao bị loại được đếm chính xác trong `exclusion_summary.csv`; ID, span và quyết định của mọi bản ghi nằm ở `records_audit.csv`.", "",
              "## Lỗi offset của code cũ", "",
              "Script gốc `read_jsonl.py` ghép `target + [MOD] + source`; vì vậy source_offset phải là **len(target)+1**. Code cũ của nhóm tách bằng len(source), nên sai khi hai chuỗi có độ dài khác nhau. Với cặp dài bằng nhau, hai cách có thể trùng kết quả và che khuất lỗi này.", "",
              "| Split | Lỗi mục tiêu 1-1 theo cách cũ | Theo giải mã đúng | Mẫu có quyết định/nhãn khác |",
              "| --- | ---: | ---: | ---: |"]
    for row in legacy_rows:
        lines.append("| {} | {} | {} | {} |".format(row["split"], row["legacy_target_records_after_filter"], row["correct_target_records_after_filter"], row["records_with_changed_retention_or_gold"]))
    lines += ["", "Đọc `legacy_mismatches.csv` để kiểm chứng từng mẫu. Các điểm mô hình ở báo cáo Week 8 thuộc pipeline cũ; chưa phải kết quả sau khi sửa chuyển nhãn. Cần dùng cách chuyển đúng khi chạy các bước tiếp theo.", "",
              "## Năm ví dụ", "",
              "| Ví dụ | ID | Loại gộp | Span source → target | Quyết định |",
              "| ---: | --- | --- | --- | --- |"]
    for example in examples:
        lines.append("| {} | {} | {} | {} → {} | {} |".format(example["example_number"], example["record_id"], example["mapped_type"] or "ngoài ba loại", " ".join(example["source_edit_tokens"]).replace("|", "\\|"), " ".join(example["target_edit_tokens"]).replace("|", "\\|"), "giữ" if example["retained"] else "loại"))
    lines += ["", "Xem bảng token đầy đủ trong `examples_5.md`; `examples_5.json` giữ cả annotation gốc và ánh xạ chỉ số.", "",
              "## Dấu vết tái lập", "",
              "`run_manifest.json` lưu SHA-256 từng JSON đầu vào, các split đã đọc và chính sách chuyển đổi. Không có tải mạng hay dependency ngoài thư viện chuẩn. Kết quả chỉ kiểm tra annotation trong file, không chứng minh dữ liệu đã gán nhãn đầy đủ hoặc đúng chuyên môn.", ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group()
    inputs.add_argument("--data-dir", type=Path, help="Directory containing train.json and dev.json (JSON or JSONL).")
    inputs.add_argument("--archive", type=Path, help="Read JSON files directly from the supplied project ZIP; do not extract or execute project code.")
    parser.add_argument("--out-dir", type=Path, default=Path("audit_outputs"))
    parser.add_argument("--include-test-counts", action="store_true", help="Explicit opt-in: structural counts only for test. No test examples or model evaluation.")
    args = parser.parse_args(argv)
    splits = ["train", "dev"] + (["test"] if args.include_test_counts else [])
    data_dir = args.data_dir or Path(__file__).resolve().parent / "data" / "json"
    all_records, fingerprints = [], {}
    archive = ZipFile(args.archive) if args.archive else None
    try:
        for split in splits:
            if archive:
                matches = [name for name in archive.namelist() if not name.startswith("__MACOSX/") and (name.endswith("/data/json/{}.json".format(split)) or name == "data/json/{}.json".format(split))]
                if len(matches) != 1:
                    raise ValueError("ZIP must contain exactly one data/json/{}.json; found {}".format(split, len(matches)))
                blob = archive.read(matches[0])
            else:
                blob = (data_dir / (split + ".json")).read_bytes()
            fingerprints[split] = {"sha256": hashlib.sha256(blob).hexdigest(), "bytes": len(blob)}
            for number, file_line, raw in load_records(blob.decode("utf-8-sig")):
                all_records.append(decode_record(raw, split, number, file_line))
    finally:
        if archive:
            archive.close()
    summary, distributions, classes, exclusions, legacy_rows, mismatches = [], [], [], [], [], []
    for split in splits:
        before = [r for r in all_records if r["split"] == split]
        after = [r for r in before if r["retained"]]
        dropped = [r for r in before if not r["retained"]]
        for stage, records in (("before_filter", before), ("after_filter", after)):
            row, distribution = stage_statistics(split, stage, records)
            summary.append(row)
            distributions.extend(distribution)
            classes.extend(class_statistics(split, stage, records))
        counts = Counter((r["mapped_type"], r["raw"]["error_type"], r["edit_kind"],
                          len(r["source_positions_clean_0based"]),
                          len([x for x in r["target_edit_tokens"] if x != NONE])) for r in dropped)
        for (label, original, reason, source_len, target_len), count in sorted(counts.items()):
            exclusions.append({"split": split, "mapped_type": label, "original_error_type": original,
                               "exclusion_reason": reason, "source_real_edit_tokens": source_len,
                               "target_real_edit_tokens": target_len, "records": count})
        changed = [r for r in before if legacy_mismatch(r)]
        legacy_rows.append({
            "split": split, "original_records": len(before),
            "legacy_records_after_filter": sum(r["legacy_retained"] for r in before),
            "correct_records_after_filter": len(after),
            "legacy_target_records_after_filter": sum(bool(r["mapped_type"]) and r["legacy_retained"] for r in before),
            "correct_target_records_after_filter": sum(bool(r["mapped_type"]) for r in after),
            "legacy_dropped_target_records": sum(not r["legacy_retained"] for r in before),
            "correct_dropped_target_records": len(dropped),
            "records_with_changed_retention_or_gold": len(changed),
        })
        for record in changed:
            row = audit_record_row(record)
            row["legacy_source_edit_tokens_json"] = json_text(record["legacy_source_edit_tokens"])
            row["legacy_target_edit_tokens_json"] = json_text(record["legacy_target_edit_tokens"])
            row["legacy_source_positions_clean_0based_json"] = json_text(record["legacy_source_positions_clean_0based"])
            mismatches.append(row)
        assert len(before) == len(after) + len(dropped)
    examples = choose_five_examples(all_records)
    manifest = {
        "input_mode": "zip" if args.archive else "directory", "splits_read": splits,
        "input_files": fingerprints, "alignment": "target + [MOD] + source",
        "source_offset": "len(target) + 1", "indexing": "0-based token indices; 1-based record numbers/file lines",
        "target_type_map": TYPE_MAP, "placeholder": NONE,
        "scope": "gold-conditioned one-source-token/one-target-token substitution subset; other types retained as O",
        "source_group_identity": "exact source token sequence after removing [NONE]; not document/sentence identity",
        "O_means": "no observed target annotation at that token in that record; not verified grammatical correctness",
        "test_examples_exported": False, "models_trained_or_scored": False,
        "raw_data_modified": False, "reconciliation_checks_passed": True,
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    tables = {
        "counts_summary.csv": summary, "class_counts.csv": classes,
        "error_count_distribution.csv": distributions, "exclusion_summary.csv": exclusions,
        "legacy_comparison.csv": legacy_rows, "legacy_mismatches.csv": mismatches,
        "records_audit.csv": [audit_record_row(r) for r in all_records],
    }
    for filename, rows in tables.items():
        write_csv(args.out_dir / filename, rows)
    (args.out_dir / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.out_dir / "examples_5.json").write_text(json.dumps(examples, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.out_dir / "examples_5.md").write_text(examples_markdown(examples), encoding="utf-8")
    (args.out_dir / "AUDIT_REPORT.md").write_text(audit_report(summary, classes, exclusions, legacy_rows, examples, fingerprints), encoding="utf-8")
    print("EXPECT count audit completed. No model was trained or scored.")
    for row in summary:
        print("{split:5} {stage:13} records={annotation_records:5} unique_sources={unique_source_texts:5} visible_tokens={visible_source_tokens_record_occurrences:6} target_edits={target_annotated_edit_records:4} target_token_positions={target_source_position_record_occurrences:4} target_gaps={target_gap_position_record_occurrences:3}".format(**row))
    for row in legacy_rows:
        print("{}: correct dropped={}, legacy dropped={}, changed records={}".format(row["split"], row["correct_dropped_target_records"], row["legacy_dropped_target_records"], row["records_with_changed_retention_or_gold"]))
    print("Saved tables and five examples to {}".format(args.out_dir))


if __name__ == "__main__":
    main()
