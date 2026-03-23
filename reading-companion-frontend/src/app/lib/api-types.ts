import type { components } from "./generated/api-schema";

type ApiSchemas = components["schemas"];

export type PageInfo = ApiSchemas["PageInfo"];
export type SearchHit = ApiSchemas["SearchHit"];
export type SourceAsset = ApiSchemas["SourceAsset"];
export type TextSpanLocator = ApiSchemas["TextSpanLocator"];
export type ReactionTargetLocator = ApiSchemas["ReactionTargetLocator"];
export type ReactionAnchor = ApiSchemas["ReactionAnchor"];
export type ReadingLocus = ApiSchemas["ReadingLocus"];
export type FeaturedReactionPreview = ApiSchemas["FeaturedReactionPreview"];
export type BookShelfCard = ApiSchemas["BookShelfCard"];
export type BooksPageResponse = ApiSchemas["BooksPageResponse"];
export type AnalysisStartAcceptedResponse = ApiSchemas["AnalysisStartAcceptedResponse"];
export type AnalysisResumeAcceptedResponse = ApiSchemas["AnalysisResumeAcceptedResponse"];
export type UploadAcceptedResponse = ApiSchemas["UploadAcceptedResponse"];
export type ErrorPayload = ApiSchemas["ErrorResponse"];
export type JobStatusResponse = ApiSchemas["JobStatusResponse"];
export type ChapterTreeItem = ApiSchemas["ChapterTreeItem"];
export type CurrentStatePanel = ApiSchemas["CurrentStatePanel"];
export type ChapterCompletionCard = ApiSchemas["ChapterCompletionCard"];
export type AnalysisStateResponse = ApiSchemas["AnalysisStateResponse"];
export type ActivityEvent = ApiSchemas["ActivityEvent"];
export type ActivityEventsPageResponse = ApiSchemas["ActivityEventsPageResponse"];
export type AnalysisLogResponse = ApiSchemas["AnalysisLogResponse"];
export type ChapterListItem = ApiSchemas["ChapterListItem"];
export type BookDetailResponse = ApiSchemas["BookDetailResponse"];
export type ReactionCard = ApiSchemas["ReactionCard"];
export type SectionCard = ApiSchemas["SectionCard"];
export type ChapterDetailResponse = ApiSchemas["ChapterDetailResponse"];
export type ChapterHeadingBlock = ApiSchemas["ChapterHeadingBlock"];
export type ChapterOutlineSectionItem = ApiSchemas["ChapterOutlineSectionItem"];
export type ChapterOutlineResponse = ApiSchemas["ChapterOutlineResponse"];
export type MarkRecord = ApiSchemas["MarkRecord"];
export type MarksPageResponse = ApiSchemas["MarksPageResponse"];
export type BookMarksGroup = ApiSchemas["BookMarksGroup"];
export type BookMarksResponse = ApiSchemas["BookMarksResponse"];
export type SetMarkRequest = ApiSchemas["SetMarkRequest"];
export type DeleteMarkResponse = ApiSchemas["DeleteMarkResponse"];

export type ApiErrorResponse = Pick<ErrorPayload, "code" | "message" | "status"> &
  Partial<Pick<ErrorPayload, "error_id" | "retryable" | "details">>;
