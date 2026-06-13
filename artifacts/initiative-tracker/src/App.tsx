import { Switch, Route, Router as WouterRouter } from "wouter";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import AppShell from "@/components/layout/AppShell";
import Dashboard from "@/pages/Dashboard";
import Initiatives from "@/pages/Initiatives";
import InitiativeDetail from "@/pages/InitiativeDetail";
import InitiativeForm from "@/pages/InitiativeForm";
import NotFound from "@/pages/not-found";

const queryClient = new QueryClient();

function Router() {
  return (
    <AppShell>
      <Switch>
        <Route path="/" component={Dashboard} />
        <Route path="/initiatives" component={Initiatives} />
        <Route path="/initiatives/new" component={InitiativeForm} />
        <Route path="/initiatives/:id/edit">
          {(params) => <InitiativeForm id={Number(params.id)} />}
        </Route>
        <Route path="/initiatives/:id">
          {(params) => <InitiativeDetail id={Number(params.id)} />}
        </Route>
        <Route component={NotFound} />
      </Switch>
    </AppShell>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, "")}>
          <Router />
        </WouterRouter>
        <Toaster />
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;
