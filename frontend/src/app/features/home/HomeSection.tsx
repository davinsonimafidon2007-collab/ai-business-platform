"use client";

import Link from "next/link";

type Props = {
  title: string;
  href: string;
  children?: React.ReactNode;
};

export function HomeSection({ title, href, children }: Props) {
  return (
    <section>
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-base font-semibold text-secondary-900 dark:text-primary-100">
          {title}
        </h2>
        <Link
          href={href}
          className="text-sm font-medium text-primary-600 hover:text-primary-700 dark:text-primary-400"
        >
          Ver todo →
        </Link>
      </div>
      {children}
    </section>
  );
}
