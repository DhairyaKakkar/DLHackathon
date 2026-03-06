import { cn } from "@/lib/utils";

function Pulse({ className }: { className?: string }) {
  return (
    <div className={cn("animate-pulse bg-black/[0.06] rounded-lg", className)} />
  );
}

export function StudentDashboardSkeleton() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <Pulse className="h-8 w-48" />
        <Pulse className="h-9 w-28" />
      </div>

      <div className="bg-white rounded-xl border border-[#d0cec9] p-8 flex flex-col items-center gap-4">
        <Pulse className="h-32 w-52 rounded-full" />
        <Pulse className="h-4 w-72" />
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="bg-white rounded-xl border border-[#d0cec9] p-5 flex flex-col gap-3">
            <Pulse className="h-4 w-24" />
            <Pulse className="h-8 w-12" />
            <Pulse className="h-1 w-full" />
          </div>
        ))}
      </div>

      <div className="bg-white rounded-xl border border-[#d0cec9] overflow-hidden">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="flex items-center gap-4 px-5 py-4 border-b border-[#ece9e4] last:border-0">
            <Pulse className="h-4 w-32" />
            <Pulse className="h-4 w-16" />
            <Pulse className="h-4 w-20 hidden md:block" />
            <Pulse className="h-4 w-20 hidden md:block" />
          </div>
        ))}
      </div>
    </div>
  );
}

export function TasksSkeleton() {
  return (
    <div className="flex flex-col gap-4">
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="bg-white rounded-xl border border-[#d0cec9] p-5 flex items-center gap-4">
          <Pulse className="h-6 w-20 rounded-full" />
          <div className="flex-1 flex flex-col gap-2">
            <Pulse className="h-4 w-3/4" />
            <Pulse className="h-3 w-1/3" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function FacultySkeleton() {
  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-3 gap-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="bg-white rounded-xl border border-[#d0cec9] p-5">
            <Pulse className="h-3 w-20 mb-3" />
            <Pulse className="h-8 w-16" />
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="bg-white rounded-xl border border-[#d0cec9] p-5">
            <Pulse className="h-4 w-32 mb-3" />
            <Pulse className="h-3 w-full mb-2" />
            <Pulse className="h-3 w-2/3" />
          </div>
        ))}
      </div>

      <div className="bg-white rounded-xl border border-[#d0cec9] p-6">
        <Pulse className="h-4 w-36 mb-4" />
        <Pulse className="h-44 w-full" />
      </div>
    </div>
  );
}
