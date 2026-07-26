import { BrowserRouter, Routes, Route, Link } from "react-router";
import UploadPage from "./pages/UploadPage";
import ChatPage from "./pages/ChatPage";
import ArchivePage from "./pages/ArchivePage";

function Landing() {
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
          <Link
            to="/upload"
            className="px-6 py-3 bg-violet-600 text-white rounded-xl font-medium hover:bg-violet-500 transition-colors cursor-pointer"
          >
            Get Started
          </Link>

          <Link
            to="/chat"
            className="px-6 py-3 border border-gray-700 text-gray-300 rounded-xl font-medium hover:border-violet-500 hover:text-white transition-colors cursor-pointer"
          >
            Learn More
          </Link>
        </div>
      </div>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      {/* Temporary nav — Priyanshu to replace with final layout/nav components */}
      <nav className="flex gap-4 p-4 border-b border-gray-800 bg-gray-950">
        <Link to="/" className="text-white">Home</Link>
        <Link to="/upload" className="text-white">Upload</Link>
        <Link to="/chat" className="text-white">Chat</Link>
        <Link to="/archive" className="text-white">Archive</Link>
      </nav>

      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/archive" element={<ArchivePage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;