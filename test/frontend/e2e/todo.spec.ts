import { expect, test, type Page } from "@playwright/test";

const password = "Password123";

function uniqueEmail(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2)}@example.com`;
}

async function register(page: Page, email: string) {
  await page.goto("/register");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByLabel("Confirm Password").fill(password);
  await page.getByRole("button", { name: "Create Account" }).click();
  await expect(page.getByRole("heading", { name: "Todo App" })).toBeVisible();
  await expect(page.getByText(email)).toBeVisible();
}

async function login(page: Page, email: string) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Sign In" }).click();
  await expect(page.getByRole("heading", { name: "Todo App" })).toBeVisible();
  await expect(page.getByText(email)).toBeVisible();
}

async function createTodo(page: Page, title: string, description?: string) {
  await page.getByRole("button", { name: "Add Todo" }).click();
  await page.getByRole("dialog").getByLabel("Title").fill(title);
  if (description) {
    await page.getByRole("dialog").getByLabel("Description (optional)").fill(description);
  }
  await page.getByRole("dialog").getByRole("button", { name: "Create" }).click();
  await expect(page.getByText(title)).toBeVisible();
}

async function logout(page: Page) {
  await page.getByRole("button", { name: "Logout" }).click();
  await expect(page).toHaveURL(/\/login$/);
}

test("full user journey: register, create todo, toggle completion, logout", async ({ page }) => {
  const email = uniqueEmail("journey");
  const todoTitle = `E2E Todo ${Date.now()}`;

  await register(page, email);
  await createTodo(page, todoTitle, "Created from Playwright");

  const todoCheckbox = page.getByLabel(todoTitle);
  await expect(todoCheckbox).not.toBeChecked();
  await todoCheckbox.check();
  await expect(todoCheckbox).toBeChecked();

  await logout(page);
  await login(page, email);
  await expect(page.getByText(todoTitle)).toBeVisible();
  await expect(page.getByLabel(todoTitle)).toBeChecked();

  await logout(page);
});

test("cross-user data isolation: user B cannot see user A todo", async ({ browser }) => {
  const userAEmail = uniqueEmail("isolation-a");
  const userBEmail = uniqueEmail("isolation-b");
  const privateTodo = `Private Todo ${Date.now()}`;

  const userAContext = await browser.newContext();
  const userAPage = await userAContext.newPage();
  await register(userAPage, userAEmail);
  await createTodo(userAPage, privateTodo);

  const userBContext = await browser.newContext();
  const userBPage = await userBContext.newPage();
  await register(userBPage, userBEmail);
  await expect(userBPage.getByText(privateTodo)).not.toBeVisible();
  await expect(userBPage.getByText("No todos yet")).toBeVisible();

  await userAContext.close();
  await userBContext.close();
});
