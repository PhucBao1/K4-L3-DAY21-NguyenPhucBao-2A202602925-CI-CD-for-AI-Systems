# Báo Cáo Lab Day 21 - CI/CD cho AI Systems

| | |
|---|---|
| Họ và tên | Nguyễn Phúc Bảo |
| MSSV | 2A202602925 |
| Lớp / Khóa | K4 |
| Repo GitHub | https://github.com/PhucBao1/K4-L3-DAY21-NguyenPhucBao-2A202602925-CI-CD-for-AI-Systems |
| Ngày nộp | 07/10/2026 |

## 1. Bộ Siêu Tham Số Đã Chọn và Lý Do

| Lần chạy | n_estimators | learning_rate | max_depth | f1_score | accuracy |
|---|---|---|---|---|---|
| 1 | 100 | 0.1 | 3 | 0.7109 | 0.878 |
| 2 | 50 | 0.05 | 2 | 0.6051 | 0.846 |
| 3 | 200 | 0.1 | 5 | 0.7149 | 0.874 |
| 4 | 200 | 0.2 | 4 | 0.6881 | 0.864 |

**Bộ siêu tham số đã chọn:** `n_estimators=200`, `learning_rate=0.1`, `max_depth=5`.

**Lý do:** Bộ này đạt F1 cao nhất; bộ 100 cây đạt accuracy cao nhất. Learning rate nhỏ có thể cần nhiều cây hơn. Do thay đổi nhiều tham số đồng thời, chưa thể kết luận tác động riêng từng tham số.

## 2. Vì Sao Ngưỡng Chất Lượng Đặt Trên F1 Chứ Không Phải Accuracy

Lớp thu nhập cao chỉ chiếm khoảng 24.8%. Mô hình luôn dự đoán thu nhập thấp vẫn đạt accuracy 75.2% nhưng F1 lớp dương bằng 0. F1 kết hợp precision và recall để đánh giá khả năng phát hiện lớp thu nhập cao. Vì vậy pipeline dùng F1 nhị phân của lớp dương với ngưỡng 0.65; không dùng weighted hoặc macro vì chúng tổng hợp cả hai lớp, không đo đúng mục tiêu này.

Khi sàng lọc người thu nhập cao, bỏ sót làm mất cơ hội nên recall quan trọng. Khi cấp tín dụng, gán nhầm có thể tốn kém hơn; lab chưa định lượng chi phí.

## 3. Khó Khăn Gặp Phải và Cách Giải Quyết

| Khó khăn | Nguyên nhân | Cách giải quyết |
|---|---|---|
| Release thất bại khi SSH. | Action không đọc được private key trong secret. | Cập nhật SERVER_SSH_KEY; run sau đã thành công. |
| Actions bị tắt trên fork. | GitHub vô hiệu hóa workflow khi fork. | Bật Actions và chạy lại pipeline. |
| Model trên S3 có thể bị thay trước gate. | Upload nằm trong job Train. | Chuyển upload vào Release, chỉ chạy sau Quality Gate (run #5 xanh). |

## 4. So Sánh Bước 2 và Bước 3

| | f1_score | accuracy |
|---|---|---|
| Bước 2 (22,361 mẫu) | 0.7149 | 0.874 |
| Bước 3 (44,722 mẫu) | 0.7354 | 0.882 |

**Nhận xét:** F1 tăng 0.0205, accuracy tăng 0.008 trên cùng holdout 500 mẫu. Commit dữ liệu d72d1a4 tự kích hoạt bốn jobs thành công. Thêm dữ liệu không đảm bảo luôn cải thiện mô hình.

## 5. Phần Bonus Đã Thực Hiện

Tất cả bonus đã chạy trên CI ở run #5 (commit 7af7ad3, ảnh `10-bonus-actions.png`).

- Bonus 2 (`06-threshold.png`): Quét 0.1–0.9, bước 0.05; ngưỡng 0.30 đạt F1 0.7537 so với 0.7354 tại 0.5; accuracy giảm còn 0.868. Ngưỡng chọn trên chính holdout nên F1 này hơi lạc quan.
- Bonus 3 (`07-detail-report.png`): Confusion matrix, precision/recall từng lớp, `detail.txt` upload cùng `report.json`.
- Bonus 4 (`08-release-comparison.png`): Release so F1 mới với `report.json` của lần triển khai trước trên S3, chỉ upload model khi không thấp hơn.
- Bonus 5 (`06-threshold.png`): Tỷ lệ lớp dương 24.78%, lệch < 5 điểm % nên không cảnh báo; ghi `positive_ratio` vào report.

**Quality gate chặn Release** (`09-quality-gate-chan.png`): run 37634677301 trên branch `demo-gate` với tham số yếu (10 / 0.01 / 1) cho F1 0.5577 < 0.65; job Quality Gate fail và Release bị skip, model trên S3/VM không bị thay. Branch này không merge vào main.
