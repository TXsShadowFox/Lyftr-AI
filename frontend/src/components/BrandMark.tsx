export function BrandMark({ className = "h-8 w-8" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 32 32"
      className={className}
      aria-hidden="true"
      focusable="false"
    >
      <rect x="0.5" y="0.5" width="31" height="31" rx="4.5" fill="#161616" stroke="#4b4b4b" />
      <path
        d="M10 8v15h12"
        fill="none"
        stroke="#fafafa"
        strokeWidth="2.25"
        strokeLinecap="square"
      />
      <path
        d="M10 8h6"
        fill="none"
        stroke="#6b8fff"
        strokeWidth="2.25"
        strokeLinecap="square"
      />
    </svg>
  );
}
