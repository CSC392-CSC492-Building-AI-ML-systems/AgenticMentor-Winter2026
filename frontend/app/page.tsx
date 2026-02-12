import Link from "next/link"

export default function LandingPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-white">
      <div className="text-center space-y-6">
        <h1 className="text-5xl font-bold">Agentic Project Mentor</h1>
        <p className="text-gray-600 text-lg">
          Transform ideas into architect-level project plans.
        </p>

        <Link
          href="/dashboard"
          className="px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition"
        >
          Go to Dashboard
        </Link>
      </div>
    </div>
  )
}
