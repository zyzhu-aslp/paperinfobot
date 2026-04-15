# 添加论文格式要求
直接在文件中追加 BibTeX 条目，支持的字段如下：
```
@inproceedings{唯一key,
  title        = {论文标题},
  author       = {姓, 名 and 姓, 名 and Xie, Lei},
  booktitle    = {Proc. ICASSP},          % 会议论文用 booktitle
  % journal    = {IEEE/ACM TASLP},        % 期刊论文用 journal
  year         = {2026},
  abbr         = {ICASSP},                % 左侧彩色标签

  % ===== 以下全部可选，填了就显示对应按钮 =====
  abstract     = {摘要文本...},            % → [Abstract] 按钮
  arxiv        = {2406.12345},            % → [arXiv] 按钮（只填ID）
  pdf          = {https://...},           % → [PDF] 按钮
  code         = {https://github.com/...},% → [Code] 按钮
  demo         = {https://...},           % → [Demo] 按钮
  website      = {https://...},           % → [Website] 按钮
  video        = {https://...},           % → [Video] 按钮
  slides       = {https://...},           % → [Slides] 按钮
  poster       = {https://...},           % → [Poster] 按钮
  bibtex_show  = {true},                  % → [Bib] 按钮（显示引用格式）
  award        = {Best Paper Award},      % → 奖项高亮标签
  award_name   = {Best Paper},            % → 自定义奖项文字
  selected     = {true},                  % → 出现在首页"近期论文"
  preview      = {图片文件名.png},         % → 左侧缩略图（放在 assets/img/publication_preview/）
}
```

## 关键字段说明

| 字段 | 必填？ | 作用 |
|------|--------|------|
| `title`, `author`, `year` | 必填 | 基本信息 |
| `booktitle` / `journal` | 必填其一 | 决定显示"In Proc. XXX"还是期刊名 |
| `abbr` | 推荐 | 左侧彩色标签，需要在 `_data/venues.yml` 中定义颜色 |
| `selected` | 可选 | 设为 `{true}` 才会出现在首页"近期论文" |
| 其余字段 | 可选 | 填了就显示按钮，不填就不显示 |