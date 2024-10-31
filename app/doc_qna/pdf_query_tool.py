import fitz  # PyMuPDF
import os
from openai import OpenAI

class PDFQueryTool():
    
    def __init__(self, api_key: str):
        """
        Initialize the tool with the OpenAI API key.
        """
        self.api_key = api_key
        self.context = []
        self.max_context_length = 10  # Limit the number of messages to keep in context

    def extract_text_from_pdf(self, pdf_file: str) -> str:
        """
        Extracts text from the provided PDF file.
        """

        print(f"Extracting text from PDF: {pdf_file}")
        doc = fitz.open(pdf_file)
        pdf_text = ""
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pdf_text += page.get_text("text")  # Extract text from each page
            
        return pdf_text

    def initialize_conversation_context(self, pdf_text: str):
        """
        Initializes the conversation context with the PDF text.
        """
        system_prompt = "You are an assistant that answers questions based on a provided document. You take each question asked, and answer each question based on the contents of the document. Your response should contain markdown for the questions and answers."
        
        print(f"Initializing conversation context with system prompt: {system_prompt}")

        self.context = [
            {"role": "system", "content": system_prompt },
            {"role": "user", "content": pdf_text}
        ]

    def _update_context(self, role: str, content: str):
        """
        Update the context with a new message and manage the context size.
        """
        self.context.append({"role": role, "content": content})
        
        # Maintain the context size by removing the oldest messages if necessary
        if len(self.context) > self.max_context_length:
            self.context.pop(1)  # Remove the oldest user message while keeping system and assistant messages

    def ask_question_with_context(self, question: str) -> str:
        """
        Asks a question to the LLM using the conversation context.
        """
        # Update the context with the user's question
        self._update_context("user", question)
        
        print(f"Context: {self.context}")

        client = OpenAI(api_key=self.api_key)
        
        response = client.chat.completions.create(
            messages=self.context,
            model="gpt-4o",
        )
        
        # Extract response and update the context
        answer = response.choices[0].message.content
        self._update_context("assistant", answer)
        
        return answer

    def reset_context(self):
        """
        Resets the conversation context.
        """
        self.context = []

    def run(self, pdf_file: str, question: str) -> str:
        """
        Runs the tool. Extracts PDF text, initializes context, and asks a question.
        """
        # Extract the text from the provided PDF
        pdf_text = self.extract_text_from_pdf(pdf_file)
        
        # Initialize the conversation context
        self.initialize_conversation_context(pdf_text)

        # Answer the user's question using context
        return self.ask_question_with_context(question)
