export default function LessonPage() {
  return (
    <main
      style={{
        minHeight: "100vh",
        background: "#f9fafb",
        padding: "32px 24px",
        fontFamily: "system-ui, sans-serif",
      }}
    >
      <div
        id="eale-lesson-root"
        style={{
          maxWidth: "960px",
          margin: "0 auto",
          background: "#fff",
          borderRadius: "16px",
          padding: "28px",
          boxShadow: "0 1px 4px rgba(0,0,0,.08)",
          minHeight: "80vh",
        }}
      >
        <p style={{ color: "#9ca3af", fontSize: "14px", textAlign: "center", marginTop: "120px" }}>
          Loading lesson from EALE extension…
        </p>
      </div>
    </main>
  );
}
