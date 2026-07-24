import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import UploadPage from "./pages/UploadPage";
import ChatPage from "./pages/ChatPage";
import ArchivePage from "./pages/ArchivePage";

function App() {
  return (
    <BrowserRouter>
      {/* Temporary nav — Priyanshu to replace with final layout/nav components */}
      <nav className="flex gap-4 p-4 border-b">
        <Link to="/upload">Upload</Link>
        <Link to="/chat">Chat</Link>
        <Link to="/archive">Archive</Link>
      </nav>

      <Routes>
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/archive" element={<ArchivePage />} />
        <Route path="/" element={<UploadPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;