import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Link, useNavigate } from "react-router-dom";
import { isAxiosError } from "axios";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useLogin } from "../api/auth";
import { loginSchema, type LoginFormData } from "../schemas/auth";

export function LoginForm() {
  const navigate = useNavigate();
  const loginMutation = useLogin();

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = (data: LoginFormData) => {
    loginMutation.mutate(data, {
      onSuccess: () => {
        toast.success("Login successful!");
        navigate("/");
      },
      onError: (error: unknown) => {
        const message = isAxiosError<{ detail?: string }>(error)
          ? error.response?.data?.detail
          : undefined;
        toast.error(message || "Login failed. Please try again.");
      },
    });
  };

  const handleAutofillDemo = () => {
    setValue("email", "demo@test.com");
    setValue("password", "Demo@123");
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="email">Email</Label>
        <Input
          id="email"
          type="email"
          placeholder="you@example.com"
          {...register("email")}
        />
        {errors.email && (
          <p className="text-sm text-destructive">{errors.email.message}</p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="password">Password</Label>
        <Input
          id="password"
          type="password"
          placeholder="••••••••"
          {...register("password")}
        />
        {errors.password && (
          <p className="text-sm text-destructive">{errors.password.message}</p>
        )}
      </div>

      <Button
        type="submit"
        className="w-full"
        disabled={loginMutation.isPending}
      >
        {loginMutation.isPending ? "Signing in..." : "Sign In"}
      </Button>

      <p className="text-center text-sm text-muted-foreground">
        Don&apos;t have an account?{" "}
        <Link to="/register" className="text-primary underline hover:no-underline">
          Sign up
        </Link>
      </p>

      <div className="mt-6 p-4 rounded-lg border bg-muted/30 hover:bg-muted/50 transition-colors text-xs space-y-2">
        <div className="flex items-center justify-between">
          <span className="font-semibold text-foreground">Demo Account</span>
          <button
            type="button"
            onClick={handleAutofillDemo}
            className="text-primary hover:underline font-medium cursor-pointer"
          >
            Autofill
          </button>
        </div>
        <div className="grid grid-cols-[60px_1fr] gap-x-2 gap-y-1 text-muted-foreground select-all">
          <span>Email:</span>
          <code className="font-mono text-primary">demo@test.com</code>
          <span>Password:</span>
          <code className="font-mono text-primary">Demo@123</code>
        </div>
      </div>
    </form>
  );
}
