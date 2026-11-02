# TicketDesk – Hệ thống tiếp nhận và xử lý yêu cầu hỗ trợ nội bộ

## 1. Thông tin dự án

- **Dự án:** Capstone – TicketDesk
- **Đơn vị thực tập:** Công ty Rainscale Việt Nam
- **Đơn vị theo dõi:** Trường Đại học Sư phạm Kỹ thuật
- **Mô tả:** Xây dựng hệ thống tiếp nhận, quản lý và xử lý các yêu cầu hỗ trợ nội bộ, giúp tối ưu quy trình trao đổi, phân công công việc và theo dõi tiến độ xử lý ticket.

## 2. Chức năng chính

### 2.1. Quản lý người dùng và phân quyền

- Hỗ trợ các vai trò:
  - Khách hàng (Customer).
  - Nhân viên hỗ trợ (Support Staff).
  - Quản lý (Manager).
- Phân quyền truy cập và thao tác dựa trên vai trò người dùng (Role-Based Access Control – RBAC).

### 2.2. Quản lý vòng đời Ticket

- Tạo và gửi yêu cầu hỗ trợ.
- Gán ticket cho nhân viên phụ trách.
- Cập nhật và thay đổi trạng thái ticket.
- Bình luận và trao đổi trong quá trình xử lý.
- Lưu trữ lịch sử thay đổi và hoạt động của ticket.

### 2.3. Quản lý tệp đính kèm

- Hỗ trợ tải lên hình ảnh và tài liệu.
- Kiểm soát dung lượng tệp tải lên.
- Giới hạn định dạng tệp được phép đính kèm.

### 2.4. Hệ thống thông báo

- Gửi thông báo qua email khi ticket được tạo hoặc có thay đổi.
- Sử dụng Celery để xử lý các tác vụ gửi email chạy nền.

### 2.5. Dashboard và thống kê

- Thống kê số lượng ticket theo trạng thái.
- Theo dõi khối lượng công việc theo từng nhân viên xử lý.
- Theo dõi thời gian xử lý và mức độ đáp ứng SLA (Service Level Agreement).

### 2.6. Xuất báo cáo

- Hỗ trợ xuất dữ liệu báo cáo dưới định dạng Excel.
- Sử dụng Celery để xử lý tác vụ xuất báo cáo chạy nền.

### 2.7. REST API

- Xác thực người dùng bằng JWT (JSON Web Token).
- Phân quyền truy cập API.
- Hỗ trợ phân trang (Pagination).
- Hỗ trợ lọc và tìm kiếm dữ liệu (Filtering).
- Tích hợp Swagger để tài liệu hóa và kiểm thử API.

## 3. Công nghệ sử dụng

| Nhóm | Công nghệ |
|---|---|
| Backend | Django, Django REST Framework |
| Database | PostgreSQL |
| Message Broker / Cache | Redis |
| Background Tasks | Celery |
| Frontend | HTMX |
| Containerization | Docker |
| Web Server / Reverse Proxy | Nginx |
| CI/CD | GitHub Actions |
| Monitoring & Error Tracking | Sentry |

## 4. Mục tiêu dự án

Xây dựng một hệ thống hỗ trợ nội bộ có khả năng tiếp nhận, phân công và theo dõi yêu cầu một cách tập trung; đảm bảo quy trình xử lý minh bạch, phân quyền rõ ràng, tự động hóa thông báo và báo cáo, đồng thời cung cấp khả năng mở rộng thông qua REST API và kiến trúc triển khai bằng Docker.