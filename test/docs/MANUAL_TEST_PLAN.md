# Manual Test Plan: Todo App Regression Scope

## 1. Scope & Objective

Muc tieu kiem thu la xac minh cac luong quan trong cua Todo app sau khi fix bug: authentication, authorization/data isolation, Todo CRUD, partial update, cache consistency va frontend session cache.

Pham vi kiem thu:
- Authentication: register, login, invalid login, logout.
- Authorization/data isolation: User A khong duoc truy cap todo cua User B.
- Todo CRUD: create, read, update, delete.
- Todo status toggle: completed true -> false.
- Partial update: update title khong lam mat description.
- Cache consistency sau create/update/delete.
- Frontend logout khong giu du lieu user cu.

## 2. Test Environment & Prerequisites

- Backend Base URL: `http://localhost:8000`
- Frontend Base URL: `http://localhost:3000`
- API docs: `http://localhost:8000/docs`
- PostgreSQL va Redis dang chay.
- Backend da chay migration moi nhat.
- Browser moi hoac incognito window de tranh cache cu.
- Test accounts co the tao moi trong qua trinh test:
  - User A: `user_a_<timestamp>@example.com` / `Password123`
  - User B: `user_b_<timestamp>@example.com` / `Password123`

## 3. Test Cases Matrix

| TC ID | Module / Feature | Scenario | Preconditions | Test Steps | Expected Result | Priority / Severity | Status |
|---|---|---|---|---|---|---|---|
| TC-AUTH-01 | Authentication | Register thanh cong voi email moi | Frontend/backend dang chay; email chua ton tai | 1. Mo `/register`.<br>2. Nhap email moi, password hop le, confirm password trung khop.<br>3. Bam `Create Account`. | User duoc tao, duoc redirect vao Todo page, hien email user tren header. | High / Critical | Not Run |
| TC-AUTH-02 | Authentication | Login thanh cong voi account da ton tai | User da register thanh cong | 1. Mo `/login`.<br>2. Nhap email/password dung.<br>3. Bam `Sign In`. | Login thanh cong, vao Todo page, hien email user tren header. | High / Critical | Not Run |
| TC-AUTH-03 | Authentication | Invalid login khong tiet lo user ton tai hay khong | Co the dung email khong ton tai hoac password sai | 1. Mo `/login`.<br>2. Nhap email khong ton tai va password bat ky.<br>3. Quan sat loi.<br>4. Lap lai voi email ton tai nhung password sai. | Ca hai truong hop deu tra loi chung dang `Invalid email or password`; khong phan biet email ton tai hay khong. | High / Security | Not Run |
| TC-AUTH-04 | Authentication | Logout thanh cong | User da login | 1. Tu Todo page bam `Logout`.<br>2. Quan sat URL va UI.<br>3. Thu truy cap `/`. | Token bi xoa, user ve `/login`, protected page khong truy cap duoc neu chua login lai. | High / Major | Not Run |
| TC-AUTHZ-01 | Authorization / Data Isolation | User A khong doc duoc todo cua User B qua API | User A va User B da register; User B co todo ID X | 1. Login User B va tao todo X.<br>2. Lay todo ID X tu response/API docs.<br>3. Dung token User A goi `GET /api/v1/todos/{X}`. | API tra `404 Not Found` hoac `403 Forbidden`; khong tra noi dung todo cua User B. | High / Critical | Not Run |
| TC-AUTHZ-02 | Authorization / Data Isolation | User A khong sua duoc todo cua User B qua API | User A va User B da register; User B co todo ID X | 1. Dung token User A goi `PUT /api/v1/todos/{X}` voi title moi.<br>2. Dung token User B doc lai todo X. | Request cua User A bi tu choi; todo cua User B khong bi thay doi. | High / Critical | Not Run |
| TC-AUTHZ-03 | Authorization / Data Isolation | User A khong xoa duoc todo cua User B qua API | User A va User B da register; User B co todo ID X | 1. Dung token User A goi `DELETE /api/v1/todos/{X}`.<br>2. Dung token User B doc lai todo X. | Request cua User A bi tu choi; todo cua User B van ton tai. | High / Critical | Not Run |
| TC-TODO-01 | Todo CRUD | Create todo thanh cong | User da login | 1. Bam `Add Todo`.<br>2. Nhap title va description.<br>3. Bam `Create`. | Todo moi hien tren UI, mac dinh `completed=false`, description dung voi input. | High / Major | Not Run |
| TC-TODO-02 | Todo CRUD | List/read todo cua user hien tai | User da login va co it nhat 1 todo | 1. Mo Todo page.<br>2. Quan sat danh sach todo.<br>3. Goi API `GET /api/v1/todos` neu can doi chieu. | Danh sach chi gom todo cua user hien tai, total/items dung. | High / Major | Not Run |
| TC-TODO-03 | Todo CRUD | Update title/description todo thanh cong | User da login va co todo | 1. Bam edit todo.<br>2. Doi title/description.<br>3. Bam `Save`.<br>4. Refresh page. | Todo hien title/description moi sau khi refresh. | Medium / Major | Not Run |
| TC-TODO-04 | Todo CRUD | Delete todo thanh cong | User da login va co todo | 1. Bam delete todo.<br>2. Refresh page hoac goi lai list todos. | Todo bi xoa va khong xuat hien lai trong UI/API list. | Medium / Major | Not Run |
| TC-TODO-05 | Todo Status | Toggle completed tu false -> true | User da login va co todo incomplete | 1. Tick checkbox cua todo.<br>2. Refresh page. | Todo van o trang thai completed, checkbox checked. | Medium / Major | Not Run |
| TC-TODO-06 | Todo Status | Toggle completed tu true -> false persist dung | User da login va co todo completed | 1. Bo tick checkbox cua todo.<br>2. Refresh page.<br>3. Goi API doc todo neu can. | Todo chuyen ve incomplete, checkbox unchecked, API tra `completed=false`. | High / Major | Not Run |
| TC-TODO-07 | Partial Update | Update title khong lam mat description | User da login va co todo co description | 1. Tao todo voi title va description.<br>2. Chi update title, khong gui/sua description.<br>3. Doc lai todo. | Title duoc cap nhat, description cu van con nguyen. | High / Major | Not Run |
| TC-CACHE-01 | Cache Consistency | Create todo invalidate cache list | User da login; Redis dang chay | 1. Goi `GET /api/v1/todos` de tao cache list.<br>2. Tao todo moi.<br>3. Goi lai `GET /api/v1/todos` ngay lap tuc. | Todo moi xuat hien ngay; khong can doi TTL cache het han. | High / Major | Not Run |
| TC-CACHE-02 | Cache Consistency | Update todo invalidate cache list | User da login va co todo; Redis dang chay | 1. Goi `GET /api/v1/todos` de tao cache list.<br>2. Update title todo.<br>3. Goi lai `GET /api/v1/todos` ngay lap tuc. | Danh sach tra title moi, khong tra title cu tu cache. | High / Major | Not Run |
| TC-CACHE-03 | Cache Consistency | Delete todo invalidate cache list | User da login va co todo; Redis dang chay | 1. Goi `GET /api/v1/todos` de tao cache list.<br>2. Delete todo.<br>3. Goi lai `GET /api/v1/todos` ngay lap tuc. | Todo da xoa khong con trong list; cache cu khong duoc tra lai. | High / Major | Not Run |
| TC-FE-01 | Frontend Session Cache | Logout khong giu du lieu user cu | User A co todo rieng; User B da ton tai hoac tao moi | 1. Login User A va tao todo `Private A`.<br>2. Logout.<br>3. Login User B tren cung browser.<br>4. Quan sat Todo page. | UI khong hien todo `Private A`; React Query/local session cache da duoc clear. | High / Critical | Not Run |
| TC-FE-02 | Frontend Query Cache | Doi user/session khong dung lai todo cache cu | User A va User B co du lieu khac nhau | 1. Login User A, mo Todo page.<br>2. Logout.<br>3. Login User B.<br>4. Refresh page va quan sat list. | User B chi thay todo cua User B; khong thay todo/cache cua User A. | High / Critical | Not Run |

## 4. Defect Tracking & Known Limitations

- Neu test fail, ghi lai: TC ID, browser/API endpoint, steps thuc te, expected vs actual, screenshot/log neu co.
- Cac cache test can Redis that dang chay; neu dung mock/local mode khong co Redis thi ket qua cache consistency khong dai dien production.
- Cac authorization test nen uu tien kiem tra bang API vi can su dung todo ID cua user khac.
- E2E tests can backend, frontend, database va Redis cung chay de mo phong luong nguoi dung that.
