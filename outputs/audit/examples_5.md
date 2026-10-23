# Năm ví dụ kiểm tra chuyển annotation sang token

Ví dụ lấy trực tiếp từ JSON; giữ nguyên lỗi và cách token hóa gốc. Chỉ số token bắt đầu từ 0.
`correction_index` đánh số trên `target + [MOD] + source`. Offset của source là `len(target) + 1`.
Nhãn O chỉ có nghĩa là không được gán một trong ba nhãn mục tiêu ở bản ghi này; không chứng minh token đúng ngữ pháp.

## Ví dụ 1 dev:000756

Giữ mẫu thay thế 1-1: SVA

- Loại gốc: `Subject-Verb Agreement`; nhãn gộp: `SVA`.
- Độ dài target/source có placeholder: 9/9; offset source: 10.
- correction_index gốc: `[4, 14]`.
- Vị trí trong target: `[4]`; trong source gốc: `[4]`; source sau bỏ [NONE]: `[4]`.
- Span sửa: `pollute` → `pollutes`.
- Quyết định: **GIỮ**; dạng edit: `substitution_1_to_1`.

Source sau bỏ placeholder:

```text
Besides , public transport pollute less than cars .
```

Target gốc:

```text
Besides , public transport pollutes less than cars .
```

| Chỉ số source gốc | Chỉ số source sạch | Token | Chiếu nhãn trước lọc | Nhãn dùng sau lọc |
| ---: | ---: | --- | --- | --- |
| 0 | 0 | Besides | O | O |
| 1 | 1 | , | O | O |
| 2 | 2 | public | O | O |
| 3 | 3 | transport | O | O |
| 4 | 4 | pollute | SVA | SVA |
| 5 | 5 | less | O | O |
| 6 | 6 | than | O | O |
| 7 | 7 | cars | O | O |
| 8 | 8 | . | O | O |

Vector nhãn sau lọc:

```json
["O", "O", "O", "O", "SVA", "O", "O", "O", "O"]
```

Annotation JSON đầy đủ, gồm cả evidence và parsing, nằm trong `examples_5.json`.

## Ví dụ 2 dev:001803

Giữ mẫu thay thế 1-1: VFORM

- Loại gốc: `Gerund`; nhãn gộp: `VFORM`.
- Độ dài target/source có placeholder: 5/5; offset source: 6.
- correction_index gốc: `[3, 9]`.
- Vị trí trong target: `[3]`; trong source gốc: `[3]`; source sau bỏ [NONE]: `[3]`.
- Span sửa: `have` → `having`.
- Quyết định: **GIỮ**; dạng edit: `substitution_1_to_1`.

Source sau bỏ placeholder:

```text
·Other ideas for have fun
```

Target gốc:

```text
·Other ideas for having fun
```

| Chỉ số source gốc | Chỉ số source sạch | Token | Chiếu nhãn trước lọc | Nhãn dùng sau lọc |
| ---: | ---: | --- | --- | --- |
| 0 | 0 | ·Other | O | O |
| 1 | 1 | ideas | O | O |
| 2 | 2 | for | O | O |
| 3 | 3 | have | VFORM | VFORM |
| 4 | 4 | fun | O | O |

Vector nhãn sau lọc:

```json
["O", "O", "O", "VFORM", "O"]
```

Annotation JSON đầy đủ, gồm cả evidence và parsing, nằm trong `examples_5.json`.

## Ví dụ 3 dev:000823

Giữ mẫu thay thế 1-1: NNUM

- Loại gốc: `Number`; nhãn gộp: `NNUM`.
- Độ dài target/source có placeholder: 7/7; offset source: 8.
- correction_index gốc: `[5, 13]`.
- Vị trí trong target: `[5]`; trong source gốc: `[5]`; source sau bỏ [NONE]: `[5]`.
- Span sửa: `failures` → `failure`.
- Quyết định: **GIỮ**; dạng edit: `substitution_1_to_1`.

Source sau bỏ placeholder:

```text
They notice any kind of failures .
```

Target gốc:

```text
They notice any kind of failure .
```

| Chỉ số source gốc | Chỉ số source sạch | Token | Chiếu nhãn trước lọc | Nhãn dùng sau lọc |
| ---: | ---: | --- | --- | --- |
| 0 | 0 | They | O | O |
| 1 | 1 | notice | O | O |
| 2 | 2 | any | O | O |
| 3 | 3 | kind | O | O |
| 4 | 4 | of | O | O |
| 5 | 5 | failures | NNUM | NNUM |
| 6 | 6 | . | O | O |

Vector nhãn sau lọc:

```json
["O", "O", "O", "O", "O", "NNUM", "O"]
```

Annotation JSON đầy đủ, gồm cả evidence và parsing, nằm trong `examples_5.json`.

## Ví dụ 4 dev:000257

Giữ bản ghi ngoài ba loại, nhãn mục tiêu toàn O

- Loại gốc: `Transitive Verb`; nhãn gộp: `ngoài phạm vi`.
- Độ dài target/source có placeholder: 4/4; offset source: 5.
- correction_index gốc: `[1, 6]`.
- Vị trí trong target: `[1]`; trong source gốc: `[1]`; source sau bỏ [NONE]: `[]`.
- Span sửa: `[NONE]` → `to`.
- Quyết định: **GIỮ**; dạng edit: `insertion`.

Source sau bỏ placeholder:

```text
Write me soon
```

Target gốc:

```text
Write to me soon
```

| Chỉ số source gốc | Chỉ số source sạch | Token | Chiếu nhãn trước lọc | Nhãn dùng sau lọc |
| ---: | ---: | --- | --- | --- |
| 0 | 0 | Write | O | O |
| 1 | — | [NONE] | placeholder, không phải token | không có |
| 2 | 1 | me | O | O |
| 3 | 2 | soon | O | O |

Vector nhãn sau lọc:

```json
["O", "O", "O"]
```

Annotation JSON đầy đủ, gồm cả evidence và parsing, nằm trong `examples_5.json`.

## Ví dụ 5 train:013924

Loại mẫu không phải 1-1; không biến thành nhãn O

- Loại gốc: `Gerund`; nhãn gộp: `VFORM`.
- Độ dài target/source có placeholder: 11/12; offset source: 12.
- correction_index gốc: `[0, 12, 13]`.
- Vị trí trong target: `[0]`; trong source gốc: `[0, 1]`; source sau bỏ [NONE]: `[0, 1]`.
- Span sửa: `To fly` → `Flying`.
- Quyết định: **LOẠI**; dạng edit: `multi_token_replacement`.

Source sau bỏ placeholder:

```text
To fly to different continents is easy nowadays but still expensive .
```

Target gốc:

```text
Flying to different continents is easy nowadays but still expensive .
```

| Chỉ số source gốc | Chỉ số source sạch | Token | Chiếu nhãn trước lọc | Nhãn dùng sau lọc |
| ---: | ---: | --- | --- | --- |
| 0 | 0 | To | VFORM | không dùng, bản ghi bị loại |
| 1 | 1 | fly | VFORM | không dùng, bản ghi bị loại |
| 2 | 2 | to | O | không dùng, bản ghi bị loại |
| 3 | 3 | different | O | không dùng, bản ghi bị loại |
| 4 | 4 | continents | O | không dùng, bản ghi bị loại |
| 5 | 5 | is | O | không dùng, bản ghi bị loại |
| 6 | 6 | easy | O | không dùng, bản ghi bị loại |
| 7 | 7 | nowadays | O | không dùng, bản ghi bị loại |
| 8 | 8 | but | O | không dùng, bản ghi bị loại |
| 9 | 9 | still | O | không dùng, bản ghi bị loại |
| 10 | 10 | expensive | O | không dùng, bản ghi bị loại |
| 11 | 11 | . | O | không dùng, bản ghi bị loại |

Vector nhãn sau lọc:

```json
null
```

`null` nghĩa là không đưa bản ghi vào benchmark 1-1, không phải đổi các token thành O.

Cách giải mã cũ giữ nhầm mẫu này: đọc source span `To` và target span `Flying`. Dùng offset đúng cho thấy đây là edit 2→1 token thật.

Annotation JSON đầy đủ, gồm cả evidence và parsing, nằm trong `examples_5.json`.
