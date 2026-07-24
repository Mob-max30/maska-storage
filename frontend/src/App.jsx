function App() {
  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-5xl font-bold text-white mb-4">
          MaskaStorage
        </h1>
        <p className="text-lg text-gray-400">
          AI-powered knowledge management — setup complete ✓
        </p>
        <div className="mt-8 flex gap-4 justify-center">
          <div className="px-6 py-3 bg-violet-600 text-white rounded-xl font-medium hover:bg-violet-500 transition-colors cursor-pointer">
            Get Started
          </div>
          <div className="px-6 py-3 border border-gray-700 text-gray-300 rounded-xl font-medium hover:border-violet-500 hover:text-white transition-colors cursor-pointer">
            Learn More
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
