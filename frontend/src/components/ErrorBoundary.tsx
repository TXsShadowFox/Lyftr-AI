import { Component, type ErrorInfo, type ReactNode } from "react";

interface ErrorBoundaryState {
  hasError: boolean;
}

export class ErrorBoundary extends Component<
  { children: ReactNode },
  ErrorBoundaryState
> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("LYFTR UI error", error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-dvh items-center justify-center bg-canvas p-6">
          <div className="w-full max-w-md border border-line bg-surface p-6">
            <div className="font-mono text-2xs uppercase tracking-[0.16em] text-danger">
              UI error
            </div>
            <h1 className="mt-3 font-mono text-xl tracking-tight text-ink">
              Something went wrong.
            </h1>
            <p className="mt-3 text-sm leading-6 text-body">
              The interface hit an unexpected error. Reload to start a fresh
              session. Conversation data already saved by the API is unaffected.
            </p>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="mt-5 inline-flex h-9 items-center border border-line-strong px-3 font-mono text-2xs uppercase tracking-[0.12em] text-ink transition hover:bg-surface-strong"
            >
              Reload interface
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
