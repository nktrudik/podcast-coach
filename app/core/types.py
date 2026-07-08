type JsonPrimitive = str | int | float | bool | None
type JsonValue = JsonPrimitive | list[JsonValue] | dict[str, JsonValue]
type DatabaseValue = str | int | float | bool | None
type DatabaseRecord = dict[str, DatabaseValue]
