import { OpportunityDetailClient } from "./OpportunityDetailClient";

export function generateStaticParams() {
  return [{ id: "placeholder" }];
}

export default function OpportunityDetailPage() {
  return <OpportunityDetailClient />;
}
