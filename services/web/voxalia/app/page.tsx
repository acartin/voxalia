import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { defaultAuthenticatedPath, sessionCookieName } from "@/lib/api";

export default async function Page() {
  const cookieStore = await cookies();
  if (cookieStore.get(sessionCookieName)?.value) {
    redirect(defaultAuthenticatedPath);
  }

  return (
    <main className="min-h-screen bg-background px-6 py-8 text-foreground">
      <div className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-6xl flex-col">
        <header className="flex min-h-14 items-center justify-between border-b">
          <div>
            <div className="text-lg font-medium">Voxalia</div>
            <div className="text-sm text-muted-foreground">Service console for managed voice reception</div>
          </div>
          <Button asChild>
            <Link href="/login">
              Sign in
              <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
        </header>

        <section className="grid flex-1 items-center gap-6 py-10 lg:grid-cols-[1fr_380px]">
          <div className="max-w-3xl">
            <h1 className="text-3xl font-light tracking-normal">Voxalia</h1>
            <p className="mt-4 text-sm leading-6 text-muted-foreground">
              A restrained B2B console for voice reception, tenant operations, CRM follow-up and service analytics.
              User, role and client administration will be resolved by the backend before customer data is exposed.
            </p>
          </div>

          <Card>
            <CardHeader>
              <div className="font-medium">Secure access</div>
              <div className="mt-1 text-sm text-muted-foreground">Phase 0 with first-party sessions and server-side tenant resolution.</div>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-muted-foreground">
              <div className="flex justify-between border-b pb-2">
                <span>Authentication</span>
                <span className="font-medium text-foreground">Active</span>
              </div>
              <div className="flex justify-between border-b pb-2">
                <span>Public registration</span>
                <span className="font-medium text-foreground">Disabled</span>
              </div>
              <div className="flex justify-between">
                <span>Multi-tenant</span>
                <span className="font-medium text-foreground">Voxalia API</span>
              </div>
            </CardContent>
          </Card>
        </section>
      </div>
    </main>
  );
}
