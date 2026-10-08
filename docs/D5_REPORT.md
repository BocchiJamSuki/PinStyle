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

## Reviewers compared

- **owner**: the project owner, blind.
- **developer**: Claude Code (developer), NOT blind: it knew the method of every item and built PinStyle. Its own criteria: the draft decides content and design colours (hard); the reference decides rendering (hard); the reference's version of the accessory is a bonus.

| Case | Method | owner | developer |
|---|---|---|---|
| pepper_bergen_flat | global-only | 3/3 | 0/3 |
| pepper_bergen_flat | PinStyle | 3/3 | 0/3 |
| pepper_bergen_flat | tencent | 0/3 | 3/3 |
| pepper_bergen_flat | alibaba | 0/3 | 0/3 |
| shichimi_flat | global-only | 1/3 | 0/3 |
| shichimi_flat | PinStyle | 1/3 | 0/3 |
| shichimi_flat | tencent | 0/3 | 3/3 |
| shichimi_flat | alibaba | 0/3 | 0/3 |

Item-level agreement, owner vs developer: 10/24.

developer notes:

- pepper_bergen_flat / PinStyle: [开发者自己的标准：草稿决定内容和固有色（硬性）；参考图决定画法（硬性）；饰品像参考图那样渲染（加分项）] 红发带是红色且在原位（好）；但背景被换成深蓝底，猫的颜色被改
- pepper_bergen_flat / PinStyle: [开发者自己的标准：草稿决定内容和固有色（硬性）；参考图决定画法（硬性）；饰品像参考图那样渲染（加分项）] 红发带是红色（好）；但背景被换，猫的颜色被改
- pepper_bergen_flat / PinStyle: [开发者自己的标准：草稿决定内容和固有色（硬性）；参考图决定画法（硬性）；饰品像参考图那样渲染（加分项）] 背景被换，猫的颜色被改；发带只部分恢复，偏粉色
- pepper_bergen_flat / alibaba: [开发者自己的标准：草稿决定内容和固有色（硬性）；参考图决定画法（硬性）；饰品像参考图那样渲染（加分项）] 画的是参考图的人物，草稿被忽略
- pepper_bergen_flat / global-only: [开发者自己的标准：草稿决定内容和固有色（硬性）；参考图决定画法（硬性）；饰品像参考图那样渲染（加分项）] 卑尔根小镇和天空背景被换成了参考图的深蓝底；猫从黄色变成了虎斑；红发带成了紫色的结
- pepper_bergen_flat / global-only: [开发者自己的标准：草稿决定内容和固有色（硬性）；参考图决定画法（硬性）；饰品像参考图那样渲染（加分项）] 卑尔根小镇和天空背景被换成了参考图的深蓝底；猫从黄色变成了虎斑；红发带成了黑色的结
- pepper_bergen_flat / global-only: [开发者自己的标准：草稿决定内容和固有色（硬性）；参考图决定画法（硬性）；饰品像参考图那样渲染（加分项）] 卑尔根小镇和天空背景被换成了参考图的深蓝底；猫从黄色变成了虎斑；红发带画成了金色饰物
- pepper_bergen_flat / tencent: [开发者自己的标准：草稿决定内容和固有色（硬性）；参考图决定画法（硬性）；饰品像参考图那样渲染（加分项）] 人物、猫、树桩、卑尔根小镇背景和红发带都在，猫保持黄色；画法是油画式笔触，与参考图接近。不足：没有用参考图那种偏暗的光线
- shichimi_flat / PinStyle: [开发者自己的标准：草稿决定内容和固有色（硬性）；参考图决定画法（硬性）；饰品像参考图那样渲染（加分项）] 弯角是刻花象牙（加分）；但发色和肤色被改，纸鹤和云纹丢了
- shichimi_flat / PinStyle: [开发者自己的标准：草稿决定内容和固有色（硬性）；参考图决定画法（硬性）；饰品像参考图那样渲染（加分项）] 弯角是刻花象牙（加分）；但发色被改，纸鹤和云纹丢了，狐狸身上覆盖着红布
- shichimi_flat / PinStyle: [开发者自己的标准：草稿决定内容和固有色（硬性）；参考图决定画法（硬性）；饰品像参考图那样渲染（加分项）] 弯角是刻花象牙（加分）；但发色被改，纸鹤飘到右边，云纹丢了
- shichimi_flat / alibaba: [开发者自己的标准：草稿决定内容和固有色（硬性）；参考图决定画法（硬性）；饰品像参考图那样渲染（加分项）] 画的是参考图的两个人物，草稿被忽略
- shichimi_flat / global-only: [开发者自己的标准：草稿决定内容和固有色（硬性）；参考图决定画法（硬性）；饰品像参考图那样渲染（加分项）] 发色从白色变成金色（固有色被改）；纸鹤和云纹丢了；弯角画成了暗红色；狐狸身上覆盖着红布
- shichimi_flat / global-only: [开发者自己的标准：草稿决定内容和固有色（硬性）；参考图决定画法（硬性）；饰品像参考图那样渲染（加分项）] 发色被改，肤色也变了；纸鹤和云纹丢了；弯角成了灰色条纹框
- shichimi_flat / global-only: [开发者自己的标准：草稿决定内容和固有色（硬性）；参考图决定画法（硬性）；饰品像参考图那样渲染（加分项）] 发色被改；弯角没了；纸鹤飘到右边；云纹丢了
- shichimi_flat / tencent: [开发者自己的标准：草稿决定内容和固有色（硬性）；参考图决定画法（硬性）；饰品像参考图那样渲染（加分项）] 构图、人物、狐狸、纸鹤、云纹都在；白发保留；画法是干净线条加柔和上色，接近参考图。不足：弯角是素白的，不是参考图那种刻花象牙
- shichimi_flat / tencent: [开发者自己的标准：草稿决定内容和固有色（硬性）；参考图决定画法（硬性）；饰品像参考图那样渲染（加分项）] 构图、人物、狐狸、纸鹤、云纹都在；白发保留；画法是干净线条加柔和上色，接近参考图。不足：弯角是素白的，多了金色环扣，不是参考图那种刻花象牙

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

## Second reviewer (added 2026-10-08, at the owner's request)

- The owner asked for a second review, with the developer applying **its own criteria** rather than the owner's. The developer review is **not blind**: Claude Code built the set and PinStyle, and knew every item's method.
- **Developer criteria:**
  - the draft decides content and design colours, such as hair colour, the cat's fur and the background (hard);
  - the reference decides the rendering: shading, brushwork and line quality (hard);
  - rendering the accessory like the reference's version of it is a bonus, not required.
- **Results** (table above):
  - Tencent 6/6 acceptable: it keeps every drawn element and the design colours.
  - Our methods 0/12: the global pass replaces the Pepper background, recolours the cat, and changes Shichimi's hair. It also drops the paper crane and the clouds.
  - Alibaba 0/6.
- **Agreement with the owner:** 10/24 items, all on rejections (Alibaba 6, plus 4 of ours on Shichimi).
- **What the disagreement shows:**
  - The verdict depends on what "finish my draft in my reference's style" means: adopt the reference's colours (owner), or keep the draft's colours and adopt only the rendering (developer).
  - Under the second reading, our global path is the weak point. It transfers too much of the reference (colours and background) and loses draft content.
  - Under the first reading, Tencent is too draft-faithful.
  - The method should make this choice explicit and controllable, for example with separate colour and rendering strengths, or with colour locks per region.
- Labels are stored in `docs/d5_review/`: `owner_labels.json`, `developer_labels.json` and `key.json`.
