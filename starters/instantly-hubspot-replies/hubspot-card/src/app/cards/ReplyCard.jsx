import React, { useState } from "react";
import { Alert, Button, Flex, hubspot, Text, TextArea } from "@hubspot/ui-extensions";

const BACKEND = "https://your-app.vercel.app";

hubspot.extend(({ context, actions }) => (
  <ReplyCard context={context} actions={actions} />
));

const ReplyCard = ({ context, actions }) => {
  const contactId = context.crm.objectId;
  const [thread, setThread] = useState(null);
  const [body, setBody] = useState("");
  const [error, setError] = useState("");

  async function loadThread() {
    setError("");
    const response = await hubspot.fetch(
      `${BACKEND}/api/hubspot/thread?contactId=${encodeURIComponent(contactId)}`,
    );
    const data = await response.json();
    if (!response.ok) {
      setError(data.message || "Could not load the thread.");
      setThread(null);
      return;
    }
    const messages = Array.isArray(data.messages) ? data.messages : [];
    if (messages.length === 0) {
      setThread({ empty: true, messages: [] });
      return;
    }
    setThread({ ...data, empty: false, messages });
  }

  async function openMql() {
    setError("");
    const response = await hubspot.fetch(`${BACKEND}/api/hubspot/reply`, {
      method: "POST",
      body: { contactId, manualMql: true, replyToUuid: thread.reply_to_uuid },
    });
    const data = await response.json();
    if (!response.ok) {
      setError(data.message || "MQL was refused.");
      return;
    }
    actions.addAlert({ type: "success", message: "Unowned MQL deal opened." });
  }

  async function send() {
    setError("");
    const response = await hubspot.fetch(`${BACKEND}/api/hubspot/reply`, {
      method: "POST",
      body: {
        contactId,
        replyToUuid: thread.reply_to_uuid,
        eaccount: thread.eaccount,
        subject: thread.subject,
        text: body,
      },
    });
    const data = await response.json();
    if (!response.ok) {
      setError(data.message || "Send was refused.");
      return;
    }
    actions.addAlert({ type: "success", message: "Reply sent from the campaign mailbox." });
    setBody("");
  }

  const mailbox = thread && thread.eaccount;
  const empty = Boolean(thread && thread.empty);
  const ready = Boolean(mailbox && body.trim() && !empty);

  return (
    <Flex direction="column" gap="sm">
      <Text>
        {mailbox
          ? `Sends from ${mailbox} in the same thread.`
          : "Sends from the campaign mailbox in the same thread."}
      </Text>
      {empty ? <Text>No Instantly thread</Text> : null}
      {error ? <Alert title="Not sent" variant="error">{error}</Alert> : null}
      <Button onClick={loadThread}>Load thread</Button>
      <TextArea name="body" label="Reply" value={body} onChange={setBody} />
      <Button onClick={openMql} disabled={!mailbox || empty}>
        Open MQL
      </Button>
      <Button onClick={send} disabled={!ready}>
        Send from the campaign mailbox
      </Button>
    </Flex>
  );
};
