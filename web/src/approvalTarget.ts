export type ApprovalTarget =
  | { kind: 'source'; itemIds: string[] }
  | { kind: 'draft'; draftIds: string[] }
  | { kind: 'formal'; pageIds: string[] }
