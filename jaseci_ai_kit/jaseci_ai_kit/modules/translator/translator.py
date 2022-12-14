from transformers import MBartForConditionalGeneration, MBart50TokenizerFast
from jaseci.actions.live_actions import jaseci_action
from typing import Union, List
from fastapi import HTTPException
import traceback
import torch


def setup():
    model = MBartForConditionalGeneration.from_pretrained(
        "facebook/mbart-large-50-many-to-many-mmt"
    )
    tokenizer = MBart50TokenizerFast.from_pretrained(
        "facebook/mbart-large-50-many-to-many-mmt"
    )
    return model, tokenizer


model, tokenizer = setup()
supported_languages = list(tokenizer.lang_code_to_id.keys())


@jaseci_action(act_group=["translator"], allow_remote=True)
def translate(text: Union[str, List[str]], src_lang: str, tgt_lang: str) -> List[str]:
    """
    Translate text from one language to another.

    Args:
        text (Union[str, List[str]]): Text to translate.
        src_lang (str): Source language.
        tgt_lang (str): Target language.

    Returns:
        List[str]: Translated text.
    """
    try:
        if src_lang not in supported_languages:
            raise ValueError(f"Unsupported source language: {src_lang}")
        if tgt_lang not in supported_languages:
            raise ValueError(f"Unsupported target language: {tgt_lang}")

        if isinstance(text, str):
            text = [text]
        tokenizer.src_lang = src_lang
        forced_bos_token_id = tokenizer.lang_code_to_id[tgt_lang]
        encoded = tokenizer(text, return_tensors="pt")
        generated_tokens = model.generate(
            **encoded,
            forced_bos_token_id=forced_bos_token_id,
        )
        return tokenizer.batch_decode(generated_tokens, skip_special_tokens=True)
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@jaseci_action(act_group=["translator"], allow_remote=True)
def fill_mask(text: str, src_lang: str, topk=10) -> List[str]:
    """
    Fill in the blank <mask> in a sentence.

    Args:
        text (str): Text to fill in the blank.
        src_lang (str): Source language.
        topk (int, optional): Number of predictions to return. Defaults to 10.

    Returns:
        List[str]: Predictions.
    """
    try:
        if src_lang not in supported_languages:
            raise ValueError(f"Unsupported source language: {src_lang}")

        text = f"</s> {text} </s> {src_lang}"
        input_ids = tokenizer([text], add_special_tokens=False, return_tensors="pt")[
            "input_ids"
        ]
        with torch.no_grad():
            logits = model(input_ids).logits

        masked_index = (input_ids[0] == tokenizer.mask_token_id).nonzero().item()
        probs = logits[0, masked_index].softmax(dim=0)
        _, predictions = probs.topk(topk)
        preds = tokenizer.decode(predictions).split()
        return preds
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@jaseci_action(act_group=["translator"], allow_remote=True)
def supported_languages() -> List[str]:
    """
    Get a list of supported languages.

    Returns:
        List[str]: List of supported languages.
    """
    return supported_languages
