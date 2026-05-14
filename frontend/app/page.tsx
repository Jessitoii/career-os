"use client";
import { useEffect, useState } from 'react';
import { Activity, Briefcase, CheckCircle2, XCircle } from 'lucide-react';

export default function Dashboard() {
  const [stats, setStats] = useState({ total_jobs: 0, total_applications: 0 });

  useEffect(() => {
    // In a real scenario, this would fetch from the FastAPI backend
    // fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/dashboard/stats`)
    setStats({ total_jobs: 145, total_applications: 12 });
  }, []);

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <header className="flex justify-between items-center pb-6 border-b border-slate-800">
        <div>
          <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-emerald-400">
            Career OS Command Center
          </h1>
          <p className="text-slate-400 mt-1">Autonomous application engine status</p>
        </div>
        <div className="flex items-center space-x-2 text-emerald-400 bg-emerald-400/10 px-4 py-2 rounded-full text-sm font-medium">
          <span className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
          </span>
          <span>System Active</span>
        </div>
      </header>

      <main className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard title="Scanned Jobs" value={stats.total_jobs} icon={<Briefcase className="text-blue-400" />} />
        <StatCard title="Applied" value={stats.total_applications} icon={<CheckCircle2 className="text-emerald-400" />} />
        <StatCard title="Pending Approval" value={3} icon={<Activity className="text-amber-400" />} />
        <StatCard title="Rejected" value={130} icon={<XCircle className="text-red-400" />} />
      </main>

      <section className="mt-12 bg-slate-800/50 border border-slate-700/50 rounded-xl p-6 shadow-xl backdrop-blur-sm">
        <h2 className="text-xl font-semibold mb-4 flex items-center">
          <Activity className="w-5 h-5 mr-2 text-blue-400" /> Live Activity Feed
        </h2>
        <div className="space-y-4 font-mono text-sm">
          <div className="flex space-x-4">
            <span className="text-slate-500">14:02:11</span>
            <span className="text-blue-400">[Scraper]</span>
            <span className="text-slate-300">Found 12 new jobs on LinkedIn matching 'Backend Developer'.</span>
          </div>
          <div className="flex space-x-4">
            <span className="text-slate-500">14:02:15</span>
            <span className="text-purple-400">[Scoring]</span>
            <span className="text-slate-300">Analyzing 'Senior FastAPI Engineer' at Stripe...</span>
          </div>
        </div>
      </section>
    </div>
  );
}

function StatCard({ title, value, icon }: { title: string, value: number, icon: React.ReactNode }) {
  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6 flex flex-col justify-between shadow-lg hover:bg-slate-800/80 transition-colors duration-300">
      <div className="flex justify-between items-start mb-4">
        <h3 className="text-slate-400 font-medium">{title}</h3>
        {icon}
      </div>
      <p className="text-3xl font-bold text-slate-100">{value}</p>
    </div>
  );
}
