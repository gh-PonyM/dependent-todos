"""Tests for utility functions."""

from dependent_todos.utils import generate_unique_id, slugify


class TestSlugify:
    """Test slugify function."""

    def test_basic_slugify(self):
        """Test basic slugification."""
        assert slugify("Hello World") == "hello-world"
        assert slugify("Test Case") == "test-case"

    def test_special_characters(self):
        """Test handling of special characters."""
        assert slugify("Hello, World!") == "hello-world"
        assert slugify("Test@Case#123") == "testcase123"

    def test_multiple_spaces_and_hyphens(self):
        """Test handling of multiple spaces and hyphens."""
        assert slugify("hello   world") == "hello-world"
        assert slugify("hello--world") == "hello-world"

    def test_leading_trailing_hyphens(self):
        """Test removal of leading/trailing hyphens."""
        assert slugify("-hello-") == "hello"
        assert slugify(" hello ") == "hello"

    def test_truncation(self):
        """Test truncation to max length."""
        result = slugify("this is a very long string that should be truncated", 20)
        assert result == "this-is-a-very-long"
        assert len(result) <= 20


class TestGenerateUniqueId:
    """Test generate_unique_id function."""

    def test_basic_generation(self):
        """Test basic ID generation."""
        existing = set()
        result = generate_unique_id("Hello World", existing)
        assert result == "hello-world"
        assert result not in existing

    def test_unique_generation(self):
        """Test generating unique IDs when conflicts exist."""
        existing = {"hello-world"}
        result = generate_unique_id("Hello World", existing)
        assert result == "hello-world-1"
        assert result not in existing

    def test_word_boundary_truncation(self):
        """Test that truncation respects word boundaries."""
        long_message = "this is a very long message that should be truncated properly"
        existing = set()
        result = generate_unique_id(long_message, existing, max_length=20)
        # Should not cut words in the middle
        assert result == "this-is-a-very-long"
        assert len(result) <= 20

    def test_word_boundary_with_counter(self):
        """Test word boundary truncation when counter is needed."""
        long_message = "this is a very long message that should be truncated properly"
        existing = {"this-is-a-very-long"}
        result = generate_unique_id(long_message, existing, max_length=20)
        # Should truncate at word boundary and add counter
        assert result == "this-is-a-very-1"
        assert len(result) <= 20

    def test_empty_message(self):
        """Test handling of empty message."""
        existing = set()
        result = generate_unique_id("", existing)
        assert result == "task"  # fallback

    def test_only_special_characters(self):
        """Test message with only special characters."""
        existing = set()
        result = generate_unique_id("!!!@@@", existing)
        assert result == "task"  # fallback

    def test_single_character_words(self):
        """Test with single character words."""
        existing = set()
        result = generate_unique_id("a b c d e f g", existing, max_length=10)
        assert result == "a-b-c-d-e"

    def test_counter_increment(self):
        """Test counter increments properly."""
        existing = {"test", "test-1", "test-2"}
        result = generate_unique_id("test", existing)
        assert result == "test-3"

    def test_max_length_edge_case(self):
        """Test edge case where max_length is very small."""
        existing = set()
        result = generate_unique_id("hello", existing, max_length=3)
        assert result == "hel"
        assert len(result) <= 3

    def test_existing_id_with_hyphen(self):
        """Test when existing ID already has a hyphen."""
        existing = {"test"}
        result = generate_unique_id("test", existing)
        assert result == "test-1"
