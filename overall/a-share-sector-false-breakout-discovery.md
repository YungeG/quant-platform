# 假突破过滤Discovery选择

- selected: `held3` and `price_breadth<=65%`
- signals/precision/recall: 136 / 61.76% / 28.19%

|确认|广度上限|信号|精确率|召回率|
|---|---:|---:|---:|---:|
|held3|50%|67|70.15%|15.77%|
|held3|55%|87|68.97%|20.13%|
|held3|60%|117|61.54%|24.16%|
|held3|65%|136|61.76%|28.19%|
|held3|70%|163|57.06%|31.21%|
|followthrough3|50%|57|71.93%|13.76%|
|followthrough3|55%|71|73.24%|17.45%|
|followthrough3|60%|94|64.89%|20.47%|
|followthrough3|65%|104|65.38%|22.82%|
|followthrough3|70%|117|60.68%|23.83%|
