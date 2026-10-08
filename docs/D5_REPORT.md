# D5 comparison report

Built by `scripts/make_report.py` from `runs/d5/review_revealed.csv`, `runs/d5/review_key.json` and `runs/d5/ledger.jsonl`.

- Reviewer: the project owner. Blind: the 24 outputs were shuffled per case and the method names hidden until the labels were saved.
- Attempts: up to 3 per method and case. For the services, attempts 2–3 name the accessory and its place. For our methods, attempts are seeds 0–2 of the same settings.
- Spend: Tencent CNY 1.20, Alibaba CNY 1.40 (each including one trial call; cap CNY 4.00).

## pepper_bergen_flat

| Method | Acceptable | Attempts until acceptable | lost detail | misplaced detail | style drift | structure change | not controllable | Reviewer notes |
|---|---|---|---|---|---|---|---|---|
| global-only (SDXL + MistoLine + IP-Adapter Plus (ours)) | 3/3 | 1 | 0 | 0 | 0 | 0 | 0 | 眼睛有点奇怪 |
| PinStyle (global + Engine A, 1 point pair (ours)) | 3/3 | 1 | 0 | 0 | 0 | 0 | 0 | 眼睛有点奇怪 |
| tencent (Tencent TokenHub hy-image-v3) | 0/3 | > 3 | 0 | 0 | 3 | 0 | 0 | 几乎和草稿一样，没学会参考色彩 |
| alibaba (Alibaba Model Studio qwen-image-edit-plus-2025-12-15) | 0/3 | > 3 | 0 | 0 | 0 | 3 | 0 | 输出是Reference图片 |

Grid: `runs/d5/report/grid_pepper_bergen_flat.png`. Source images: David Revoy, Pepper&Carrot, CC BY 4.0.

## shichimi_flat

| Method | Acceptable | Attempts until acceptable | lost detail | misplaced detail | style drift | structure change | not controllable | Reviewer notes |
|---|---|---|---|---|---|---|---|---|
| global-only (SDXL + MistoLine + IP-Adapter Plus (ours)) | 1/3 | 3 | 0 | 1 | 0 | 0 | 0 | 狐狸的形象发生了异变,将尾巴识别为另一只腿 |
| PinStyle (global + Engine A, 1 point pair (ours)) | 1/3 | 3 | 0 | 2 | 0 | 0 | 0 | 狐狸的形象发生了异变,将尾巴识别为另一只腿 |
| tencent (Tencent TokenHub hy-image-v3) | 0/3 | > 3 | 3 | 0 | 0 | 0 | 0 | 女孩的头发颜色没有根据reference来 |
| alibaba (Alibaba Model Studio qwen-image-edit-plus-2025-12-15) | 0/3 | > 3 | 0 | 0 | 0 | 3 | 0 | 输出是Reference图片 |

Grid: `runs/d5/report/grid_shichimi_flat.png`. Source images: David Revoy, Pepper&Carrot, CC BY 4.0.

## Interpretation (developer; facts above, reading below)

1. **Owner's blind verdict:** our two methods are tied, and both are ahead of the two services on these 2 cases.
   - Pepper: 3/3 acceptable for each of our methods.
   - Shichimi: 1/3 for each of our methods. The failure is the fox's tail turning into a leg, which comes from the shared global pass.
   - Tencent and Alibaba: 0/6 each.
2. **PinStyle and global-only received identical labels in every seed.** At whole-image size, the accessory difference measured in D3b was not what decided acceptability. That result was: carved horn 6/6 with the reference point on the horn, and 0/6 with it on the background. The reviewer judged mainly global style and structure.
   - **Consequence:** the demo should show the accessory with a zoomed crop (as in the D3 figure) if the detail is the point.
   - Whether whole-image acceptability is the right measure is an RQ1/RQ3 question.
3. **The reviewer's criterion for colour differs from the developer's instructions.**
   - Before the review, the developer wrote that a hair colour changed from the draft counts as style drift.
   - The reviewer instead expected colours, including hair colour, to follow the reference. This is why Tencent was rejected ("几乎和草稿一样，没学会参考色彩"; "女孩的头发颜色没有根据reference来").
   - The labels are reported as given.
4. **Alibaba returned the reference's content in 6/6.** This may depend on input order, which was set from the documentation (the draft last). It was not explored further, because of the 3-attempt cap.
5. **Limits:**
   - 2 cases, 1 reviewer (the owner), simulated drafts derived from the finished works;
   - our "attempts" are seeds, not refinements;
   - Midjourney is not included.
