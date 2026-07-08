export interface Project {
  _id: string;
  title: string;
  description: string | null;
  owner: string | UserInfo;
  members: Array<string | UserInfo>;
  createdAt: string;
  updatedAt: string;
  tasks: Task[];
  board: string | { _id: string; title: string };
  orderInBoard?: number;
}

export interface User {
  _id: string;
  email: string;
  name: string;
  createdAt: string;
  updatedAt: string;
}

export interface UserInfo {
  _id: string;
  name: string;
  email: string;
}

export interface Session {
  user: UserInfo;
  accessToken: string;
}

export interface BoardDocument {
  _id: string;
  title: string;
  description?: string;
  owner: string;
  members: string[];
  projects: string[];
  createdAt: string;
  updatedAt: string;
}

export enum TaskStatus {
  TODO = "TODO",
  IN_PROGRESS = "IN_PROGRESS",
  DONE = "DONE"
}

export interface Task {
  _id: string;
  id?: string;
  title: string;
  description?: string | null;
  status: TaskStatus;
  dueDate?: Date | null;
  board: string;
  project: string;
  assignee?: UserInfo;
  creator: UserInfo;
  lastModifier: UserInfo;
  orderInProject?: number;
  createdAt: string;
  updatedAt: string;
  _deleted?: boolean;
}

export interface Board {
  _id: string;
  title: string;
  description?: string;
  owner: string | UserInfo;
  members: UserInfo[];
  projects: Project[];
  createdAt: string;
  updatedAt: string;
}

export interface CreateTaskInput {
  title: string;
  description?: string;
  status?: TaskStatus;
  dueDate?: Date;
  board: string;
  project: string;
  assignee?: string;
  orderInProject?: number;
}

export interface UpdateTaskInput {
  title?: string;
  description?: string | null;
  status?: TaskStatus;
  dueDate?: Date | null;
  assigneeId?: string | null;
  lastModifier: string;
  orderInProject?: number;
  /** Optimistic lock: updatedAt the client last saw; server 409s if stale. */
  updatedAt?: string;
}
