# Thiết Kế: Tính Năng Tự Động Bình Luận & Ghim Link Affiliate (Auto-Comment & Pin Product Link)

## 1. Mục Đích & Bối Cảnh (Intent & Why)

### Bối cảnh
Khi làm tiếp thị liên kết (Affiliate Marketing) trên các nền tảng video ngắn (TikTok, Facebook Reels, Threads, YouTube Shorts), việc để đường link dẫn sang sàn thương mại điện tử (Shopee, TikTok Shop, Lazada, bio link...) trực tiếp trong phần **caption** thường bị các thuật toán mạng xã hội nhận diện là nội dung kéo người dùng ra khỏi nền tảng, dẫn đến việc bị giảm lượt phân phối tự nhiên (**bóp reach**).

### Giải pháp
Chiến lược tối ưu đã được chứng minh hiệu quả nhất trong ngành là:
- Giữ caption thuần nội dung hấp dẫn kèm hashtag để đạt lượt hiển thị tối đa.
- Đặt đường link sản phẩm vào **bình luận đầu tiên (First Comment)** ngay sau khi video vừa xuất bản.
- Tự động **Ghim bình luận (Pin Comment)** lên đầu trang để link sản phẩm luôn luôn ở vị trí đập vào mắt người xem đầu tiên, không bị trôi khi có bình luận mới từ khán giả.

---

## 2. Mục Tiêu (Goals, Non-Goals, Anti-Goals)

### Goals (Mục tiêu bắt buộc)
1. **Giao diện nhập liệu linh hoạt (Frontend):**
   - Bổ sung khu vực cấu hình **Affiliate Link & Comment** dùng chung cho cả 4 nền tảng.
   - Hỗ trợ dán link sản phẩm (URL).
   - Tích hợp nút **"Tạo câu dẫn AI"** sử dụng Gemini API để sinh tự động câu bình luận kêu gọi hành động (Call-To-Action) tự nhiên, hấp dẫn dựa trên thông tin sản phẩm và ngữ cảnh video.
   - Cung cấp ô textarea cho phép người dùng tự do xem trước, chỉnh sửa hoặc tự gõ toàn bộ nội dung bình luận theo ý muốn.
   - Tùy chọn checkbox bật/tắt: "Tự động ghim bình luận (Pin Comment)".
2. **Backend API & Payload:**
   - Cung cấp endpoint `POST /api/ai/generate-comment` nhận `product_link` và thông tin ngữ cảnh (`product_name` hoặc `topic`), trả về câu bình luận mẫu.
   - Cập nhật payload `PublishRequest` với trường `comment_config` gồm `enabled: bool`, `comment_text: str`, `pin: bool`.
3. **Thực thi Playwright (Phương án 1 - Integrated Pipeline):**
   - Ngay sau khi video xuất bản thành công trên từng nền tảng, uploader tận dụng luôn phiên trình duyệt đang mở để:
     - Truy cập bài viết vừa đăng (kèm cơ chế đối soát chống comment nhầm bài cũ).
     - Nhập và gửi bình luận.
     - Thực hiện thao tác ghim bình luận theo cơ chế linh hoạt (Best-effort Pinning).
4. **Cô lập lỗi (Fault Isolation):**
   - Nếu bước bình luận hoặc ghim gặp trục trặc (do mạng chậm hoặc nền tảng tạm thời giới hạn), trạng thái đăng video **vẫn phải được tính là thành công**, kèm log cảnh báo chi tiết thay vì làm sập toàn bộ pipeline.

### Non-Goals (Không thuộc phạm vi)
- Không lưu trữ và quản lý kho danh mục sản phẩm (Product Catalog) phức tạp trong phiên bản này.
- Không tự động trả lời (Auto-reply) các bình luận của người xem khác.

### Anti-Goals (Điều cấm kỵ)
- Tuyệt đối không comment nhầm vào các bài viết cũ hoặc bài viết ghim trước đó của tài khoản.
- Không để lỗi ở bước comment làm ngắt quãng luồng xuất bản video của các nền tảng tiếp theo.

---

## 3. Các Phương Án Đã Cân Nhắc (Approaches)

### Phương án 1: Tích hợp trực tiếp vào luồng xuất bản (ĐƯỢC CHỌN)
- **Cơ chế:** Ngay sau khi video được xác nhận xuất bản trên trang, uploader thực thi luôn bước comment và pin trước khi đóng page/context.
- **Ưu điểm:** Nhanh nhất, tận dụng session đang mở, tỷ lệ định vị bài viết vừa tạo cao nhất, log hiển thị liền mạch.
- **Đánh đổi:** Tăng thời gian giữ tab thêm ~10–15s cho mỗi nền tảng.

### Phương án 2: Luồng comment độc lập (Post-Publish Separate Job)
- **Cơ chế:** Sau khi cả 4 nền tảng đăng video xong, một service riêng mở lại từng nền tảng để tìm video và comment.
- **Ưu điểm:** Tách biệt độc lập giữa đăng bài và comment.
- **Đánh đổi:** Phức tạp, phải mở lại trình duyệt từ đầu, nhiều nền tảng không cung cấp link bài viết ngay lập tức trên web.

---

## 4. Thiết Kế Chi Tiết Hệ Thống (Detailed Design)

### 4.1. Cấu trúc Dữ liệu & API Contracts

#### Backend Model: `AffiliateCommentConfig`
```python
class AffiliateCommentConfig(BaseModel):
    enabled: bool = False
    product_link: str = ""
    comment_text: str = ""
    pin: bool = True
```

Cập nhật `PublishRequest`:
```python
class PublishRequest(BaseModel):
    video_path: str
    platforms: Dict[str, PlatformPublishConfig]
    comment_config: Optional[AffiliateCommentConfig] = None
```

#### API Sinh câu dẫn: `POST /api/ai/generate-comment`
- **Request:** `{ "product_link": "string", "context": "string" }`
- **Response:** `{ "comment_text": "string" }`
- **System Prompt:** Yêu cầu Gemini tạo 1 câu bình luận ngắn gọn, khéo léo, tự nhiên, kèm link sản phẩm ở cuối, kích thích tương tác (VD: "Nhiều bạn hỏi link áo/đồ decor này quá, mình để link chính hãng săn sale ở đây nha: ...").

---

### 4.2. Luồng Thực Thi Trên Từng Nền Tảng & Quyết Định Kỹ Thuật (Decisions)

Mỗi uploader thực thi:
`async def post_comment_and_pin(self, page: Page, comment_text: str, pin: bool = True, log_callback: Optional[Callable] = None) -> bool`

#### Cơ chế Ghim Linh Hoạt (Best-effort Pinning - Quyết định kỹ thuật của Builder):
- **YouTube Shorts:** Hỗ trợ Ghim 100% trên giao diện Desktop (Menu 3 chấm của comment $\to$ "Pin / Ghim nhận xét").
- **TikTok & Facebook & Threads:** Giao diện Desktop Web có thể không luôn hiển thị nút "Ghim" (vốn chỉ có trên app di động). Do đó hệ thống sẽ:
  1. Kiểm tra menu `...` của bình luận vừa đăng: nếu có nút "Pin comment" / "Ghim bình luận" thì thực hiện click.
  2. Nếu không tìm thấy tùy chọn Ghim trên web desktop, hệ thống ghi log: `[info] Đã gửi bình luận thành công (nền tảng không hỗ trợ ghim trên bản web desktop)` và tiếp tục quy trình an toàn, không coi là lỗi.

#### Cơ chế Đối Soát Chống Comment Nhầm Bài Cũ (Verification - Quyết định kỹ thuật của Builder):
- Trước khi gửi comment, uploader kiểm tra đối soát bài viết:
  - So khớp tiêu đề/caption với caption của video vừa xuất bản.
  - Hoặc đối soát timestamp ("vừa xong" / "just now" / mục đầu tiên trong tab quản lý content của TikTok Studio).
  - Nếu quá 45 giây mà bài viết mới chưa xuất hiện trên feed/profile (do Meta/TikTok đang xử lý ngầm), hệ thống sẽ chủ động hủy bước comment và cảnh báo: *"Video mới đang được xử lý ngầm, đã bỏ qua bước comment để tránh gửi nhầm vào bài cũ"*.

#### 1. Meta Threads (`threads.py`)
- Sau khi banner `Posting...` hoàn tất:
- Truy cập bài viết vừa đăng trên trang cá nhân.
- Tìm ô trả lời `Reply to...` / `Trả lời...`.
- Nhập `comment_text` bằng `page.keyboard.insert_text()`.
- Bấm `Post` / `Đăng`.

#### 2. TikTok Studio / Web (`tiktok.py`)
- Sau khi xuất bản: Điều hướng sang trang quản lý nội dung TikTok Studio (`/content`).
- Video mới nhất nằm ở dòng đầu tiên của bảng quản lý $\to$ Lấy link xem hoặc mở xem video.
- Nhập `comment_text` vào khung bình luận và gửi.
- Thử nghiệm thao tác Ghim nếu có menu `...`.

#### 3. Facebook Reels (`facebook.py`)
- Hỗ trợ cả **Profile** lẫn **Fanpage**:
  - Với **Profile**: Mở tab Reels trên profile cá nhân, đối soát bài mới nhất.
  - Với **Fanpage**: Truy cập trang Fanpage (`facebook.com/{page_id}`), mở tab Thước phim/Reels của Trang.
- Mở khung bình luận của Reel, nhập `comment_text` và bấm gửi.
- Thử nghiệm thao tác Ghim nếu có menu `...`.

#### 4. YouTube Shorts (`youtube.py`)
- Trích xuất link xem video ngắn `https://youtu.be/...` trực tiếp từ modal hoàn tất của YouTube Studio.
- Điều hướng tới video watch page.
- Cuộn xuống khu vực bình luận, nhập `comment_text` và gửi.
- Bấm menu 3 chấm $\to$ Chọn **Pin / Ghim** $\to$ Xác nhận modal.

---

### 4.3. Thiết Kế Giao Diện Frontend (React)

- Card riêng biệt: **"Gắn Link Sản Phẩm & Comment (Affiliate)"** đặt tại cột trái.
- Các trường:
  - Toggle Switch: Bật/Tắt tính năng Auto-Comment.
  - Input field: "Đường link sản phẩm (Shopee, TikTok Shop, Bio...)"
  - Input field: "Tên / Mô tả ngắn sản phẩm" (Tùy chọn: nhập tên sản phẩm, hoặc để trống để AI tự động lấy theo tiêu đề/chủ đề video).
  - Nút bấm: "✨ Sinh câu dẫn AI" (kèm hiệu ứng loading).
  - Textarea: "Nội dung bình luận" (cho phép gõ tay, chèn link hoặc xem trước câu do AI tạo).
  - Checkbox: "Tự động ghim bình luận (Pin comment)".
