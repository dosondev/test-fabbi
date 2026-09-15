import { AuthLayout } from "@/features/auth/components/AuthLayout";
import { RegisterForm } from "@/features/auth/components/RegisterForm";

export function RegisterPage() {
  return (
    <AuthLayout
      title="Create Account"
      subtitle="Sign up for a new account"
    >
      <RegisterForm />
    </AuthLayout>
  );
}
