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
    <nav className="bg-[#09090f]/80 backdrop-blur-xl border-b border-white/[0.06] sticky top-0 z-20">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 h-14 flex items-center gap-4">
        {/* Back link or logo */}
        {backHref ? (
          <Link
            href={backHref}
            className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-slate-200 transition-colors"
          >
            <span className="text-base">←</span>
            {backLabel ?? "Back"}
          </Link>
        ) : (
          <Link href="/" className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-md bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center">
              <BrainCircuit className="w-3.5 h-3.5 text-white" />
            </div>
            <span className="font-bold text-sm tracking-tight text-white">EALE</span>
          </Link>
        )}

        {/* Separator */}
        {title && (
          <span className="text-white/20 hidden sm:block">|</span>
        )}
        {title && (
          <span className="text-sm font-semibold text-slate-300 truncate hidden sm:block">
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
