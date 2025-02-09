import React from "react";
import Search from "./Search";
import "./App.css"; // Import global styles

const App = () => {
  return (
    <div className="app">
      <header>
        <h1>📜 Case Law Search</h1>
        <p>Find and analyze legal cases with AI-powered summaries.</p>
      </header>
      <Search />
      <footer>
        <p>Powered by CourtListener & OpenAI</p>
      </footer>
    </div>
  );
};

export default App;