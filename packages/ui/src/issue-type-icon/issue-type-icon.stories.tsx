import type { Meta, StoryObj } from "@storybook/react";
import { IssueTypeIcon } from "./issue-type-icon";

const meta: Meta<typeof IssueTypeIcon> = {
  title: "Work items/IssueTypeIcon",
  component: IssueTypeIcon,
};

export default meta;
type Story = StoryObj<typeof IssueTypeIcon>;

export const Requirement: Story = { args: { typeName: "Requirement", color: "#3B82F6" } };
export const Bug: Story = { args: { typeName: "Bug", color: "#DC2626" } };
export const Task: Story = { args: { typeName: "Task", color: "#16A34A" } };
export const Custom: Story = { args: { typeName: "Custom" } };
