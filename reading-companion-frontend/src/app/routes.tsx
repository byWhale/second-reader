import { createBrowserRouter, Navigate, useParams } from "react-router";
import { RootLayout } from "./components/layout";
import { LandingPage } from "./components/landing-page";
import { BookshelfPage } from "./components/bookshelf-page";
import { AnalysisPage } from "./components/analysis-page";
import { BookOverviewPage } from "./components/book-overview-page";
import { ChapterReadPage } from "./components/chapter-read-page";
import { GlobalMarksPage } from "./components/global-marks-page";
import { UploadPage } from "./components/upload-page";

function LegacyBookRedirect() {
  const { bookId = "" } = useParams();
  return <Navigate to={`/books/${bookId}`} replace />;
}

function LegacyChapterRedirect() {
  const { bookId = "", chapterId = "" } = useParams();
  return <Navigate to={`/books/${bookId}/chapters/${chapterId}`} replace />;
}

function LegacyAnalysisRedirect() {
  const { bookId = "" } = useParams();
  return <Navigate to={`/books/${bookId}/analysis`} replace />;
}

function LegacyBooksRedirect() {
  return <Navigate to="/books" replace />;
}

function LegacyMarksRedirect() {
  return <Navigate to="/marks" replace />;
}

function LegacySampleRedirect() {
  return <Navigate to="/books" replace />;
}

export const router = createBrowserRouter([
  {
    path: "/",
    Component: RootLayout,
    children: [
      { index: true, Component: LandingPage },
      { path: "upload", Component: UploadPage },
      { path: "sample", Component: LegacySampleRedirect },
      { path: "books", Component: BookshelfPage },
      { path: "marks", Component: GlobalMarksPage },
      { path: "bookshelf", Component: LegacyBooksRedirect },
      { path: "bookshelf/marks", Component: LegacyMarksRedirect },
      { path: "analysis/:bookId", Component: LegacyAnalysisRedirect },
      { path: "book/:bookId", Component: LegacyBookRedirect },
      { path: "book/:bookId/chapter/:chapterId", Component: LegacyChapterRedirect },
      { path: "books/:bookId", Component: BookOverviewPage },
      { path: "books/:bookId/analysis", Component: AnalysisPage },
      { path: "books/:bookId/chapters/:chapterId", Component: ChapterReadPage },
    ],
  },
]);
