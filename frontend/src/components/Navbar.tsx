import Link from "next/link";

interface NavbarProps {
  backHref?: string;
  backLabel?: string;
  title?: string;
  action?: React.ReactNode;
}

export default function Navbar({ backHref, backLabel, title, action }: NavbarProps) {
  return (
    <nav className="bg-white border-b border-[#d0cec9] sticky top-0 z-20">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 h-14 flex items-center gap-4">
        {backHref ? (
          <Link
            href={backHref}
            className="flex items-center gap-1.5 text-sm text-[#5c5c6e] hover:text-[#111113] transition-colors font-medium"
          >
            <span className="text-base">←</span>
            {backLabel ?? "Back"}
          </Link>
        ) : (
          <Link href="/" className="flex items-center gap-2">
            <div className="w-7 h-7 rounded bg-[#111113] flex items-center justify-center">
              <span className="font-display italic font-bold text-sm text-white leading-none">E</span>
            </div>
            <span className="font-display italic font-bold text-base text-[#111113] tracking-tight">EALE</span>
          </Link>
        )}

        {title && <span className="text-[#d0cec9] hidden sm:block">|</span>}
        {title && (
          <span className="text-sm font-medium text-[#5c5c6e] truncate hidden sm:block">
            {title}
          </span>
        )}

        <div className="flex-1" />
        {action}
      </div>
    </nav>
  );
}
