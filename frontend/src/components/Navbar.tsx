import Link from "next/link";
import { BrainCircuit } from "lucide-react";

interface NavbarProps {
  backHref?: string;
  backLabel?: string;
  title?: string;
  action?: React.ReactNode;
}

export default function Navbar({ backHref, backLabel, title, action }: NavbarProps) {
  return (
    <nav className="bg-white border-b border-gray-200 sticky top-0 z-20">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 h-14 flex items-center gap-4">
        {/* Back link or logo */}
        {backHref ? (
          <Link
            href={backHref}
            className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors"
          >
            <span className="text-base">←</span>
            {backLabel ?? "Back"}
          </Link>
        ) : (
          <Link href="/" className="flex items-center gap-2 text-indigo-600">
            <BrainCircuit className="w-5 h-5" />
            <span className="font-bold text-sm tracking-tight">EALE</span>
          </Link>
        )}

        {/* Title */}
        {title && (
          <span className="text-gray-200 hidden sm:block">|</span>
        )}
        {title && (
          <span className="text-sm font-semibold text-gray-700 truncate hidden sm:block">
            {title}
          </span>
        )}

        {/* Spacer */}
        <div className="flex-1" />

        {/* Action slot */}
        {action}
      </div>
    </nav>
  );
}
