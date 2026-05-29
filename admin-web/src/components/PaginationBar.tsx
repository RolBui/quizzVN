import { ChevronLeft, ChevronRight } from "lucide-react";

interface PaginationBarProps {
  page: number;
  pageSize: number;
  totalItems: number;
  onPageChange: (page: number) => void;
}

function buildPageItems(currentPage: number, totalPages: number) {
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, index) => index + 1);
  }

  const pages = new Set([1, totalPages, currentPage]);
  if (currentPage > 2) {
    pages.add(currentPage - 1);
  }
  if (currentPage < totalPages - 1) {
    pages.add(currentPage + 1);
  }

  const sortedPages = Array.from(pages).sort((first, second) => first - second);
  return sortedPages.flatMap((pageNumber, index) => {
    const previousPage = sortedPages[index - 1];
    if (index > 0 && previousPage && pageNumber - previousPage > 1) {
      return [`gap-${previousPage}-${pageNumber}`, pageNumber] as const;
    }
    return [pageNumber] as const;
  });
}

export function PaginationBar({
  page,
  pageSize,
  totalItems,
  onPageChange,
}: PaginationBarProps) {
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
  const pageItems = buildPageItems(page, totalPages);

  if (totalPages <= 1) {
    return null;
  }

  return (
    <div className="flex justify-center bg-background py-3">
      <div className="flex items-center gap-1">
        <button
          type="button"
          onClick={() => onPageChange(Math.max(1, page - 1))}
          disabled={page === 1}
          className="flex h-8 w-8 items-center justify-center rounded-md border border-outline-variant text-outline hover:bg-surface-container-low hover:text-on-surface disabled:opacity-40"
          aria-label="Trang trước"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>

        {pageItems.map((pageItem) =>
          typeof pageItem === "number" ? (
            <button
              key={pageItem}
              type="button"
              onClick={() => onPageChange(pageItem)}
              className={`h-8 min-w-8 rounded-md px-2 text-sm font-semibold ${
                pageItem === page
                  ? "bg-primary text-on-primary"
                  : "border border-outline-variant text-outline hover:bg-surface-container-low hover:text-on-surface"
              }`}
            >
              {pageItem}
            </button>
          ) : (
            <span
              key={pageItem}
              className="flex h-8 min-w-8 items-center justify-center text-outline"
            >
              ...
            </span>
          ),
        )}

        <button
          type="button"
          onClick={() => onPageChange(Math.min(totalPages, page + 1))}
          disabled={page === totalPages}
          className="flex h-8 w-8 items-center justify-center rounded-md border border-outline-variant text-outline hover:bg-surface-container-low hover:text-on-surface disabled:opacity-40"
          aria-label="Trang sau"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
