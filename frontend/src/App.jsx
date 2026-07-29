import { BrowserRouter, Routes, Route, NavLink } from "react-router";
import UploadPage from "./pages/UploadPage";
import ChatPage from "./pages/ChatPage";
import ArchivePage from "./pages/ArchivePage";

const navItems = [
  { to: "/chat", label: "Chat" },
  { to: "/upload", label: "Upload" },
  { to: "/archive", label: "Archive" },
];

function Sidebar() {
  return (
    <aside className="w-64 shrink-0 bg-[#171717] border-r border-white/10 flex flex-col">
      <div className="px-4 py-4 border-b border-white/10">
        <span className="text-white font-medium">MaskaStorage</span>
      </div>

      <nav className="flex-1 p-2 space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `block rounded-lg px-3 py-2 text-sm transition-colors ${
                isActive
                  ? "bg-white/10 text-white"
                  : "text-gray-400 hover:bg-white/5 hover:text-white"
              }`
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="p-4 text-xs text-gray-500 border-t border-white/10">
        RAG over your saved URLs and PDFs
      </div>
    </aside>
  );
}

function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen bg-[#212121]">
        <Sidebar />
        <main className="flex-1 overflow-hidden">
          <Routes>
            <Route path="/" element={<ChatPage />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/archive" element={<ArchivePage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;