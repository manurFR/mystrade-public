function correspondingCommodityInHand(commodityInTabTrade, filterOnlySelected) {
    var commodityId = $(commodityInTabTrade).data("commodityId");
    var indexInThisCommodity = $("#zone_selected_commodities").find(".commodity_card[data-commodity-id=" + commodityId + "]").index(commodityInTabTrade);
    var candidates = $("#zone_commodities").find(".commodity_card[data-commodity-id=" + commodityId + "]");
    if (filterOnlySelected) {
        candidates = candidates.filter(".card_selected");
    }
    return candidates.get(indexInThisCommodity);
}

function correspondingRulecardInHand(rulecardInTabTrade, filterOnlySelected) {
    var rihId = $(rulecardInTabTrade).data("rihId");
    var candidates = $("#zone_rulecards").find(".rulecard[data-rih-id=" + rihId + "]");
    if (filterOnlySelected) {
        candidates = candidates.filter(".card_selected");
    }
    return candidates;
}

function refreshSelectedCommodities() {
    var selectedCommodities = "";
    var currentCommodityId = 0;
    $("#zone_commodities").find(".commodity_card").not(".not_tradable, .not_submitted").each(function () {
        if ($(this).data("commodityId") != currentCommodityId) {
            currentCommodityId = $(this).data("commodityId");
            var numberOfThisCommodity = parseInt($("input#id_commodity_" + currentCommodityId).val(), 10);
            for (var i = 0; i < numberOfThisCommodity; i++) {
                selectedCommodities +=
                    '{% include "common/commodity_card.html" with name="#name#" commodity_id="#commodityId#" color="#color#" extra_classes="selectable"%}'
                        .replace("#name#", $(this).data("name")).replace("#commodityId#", ""+currentCommodityId)
                        .replace("#color#", $(this).css("background-color"));
            }
        }
    });
    $("#zone_selected_commodities").html(selectedCommodities)
        .find(".commodity_card").on("click.tradeselect", function(event) {
            clickOnCommodity(correspondingCommodityInHand(event.target, true));
        });
}

function refreshSelectedRulecards() {
    var selectedRulecards = "";
    $("#zone_rulecards").find(".rulecard").not(".not_tradable, .former").each(function() {
        var currentRihId = $(this).data("rihId");
        if ($("input#id_rulecard_" + currentRihId).val() === "True") {
            selectedRulecards += '<div class="rulecard_thumbnail selectable" data-rih-id="' + currentRihId + '">' + $(this).data("publicName") + '</div>';
        }
    });
    $("#zone_selected_rulecards").html(selectedRulecards)
        .find(".rulecard_thumbnail").on("click.tradeselect", function(event) {
            clickOnRulecard(correspondingRulecardInHand(event.target, true));
        });
}

// in trade mode, clicking on a card will add/remove it from the trade
// in initial mode, it will initiate a new trade and add the card
function clickOnCommodity(cardElement) {
    var commodityId = $(cardElement).data("commodityId");
    var hiddenInput = $("input#id_commodity_" + commodityId);
    var currentNumber = parseInt(hiddenInput.val(), 10) || 0;
    if ($(cardElement).hasClass("card_selected")) {
        hiddenInput.val(currentNumber - 1);
    } else {
        hiddenInput.val(currentNumber + 1);
    }
    $(cardElement).toggleClass("card_selected");
    if (currentMode === "initial") {
        currentMode = "createTrade";
        $("#zone_tabs").tabs("option", "active", 1);
    }
    refreshSelectedCommodities();
}

function clickOnRulecard(cardElement) {
    var rihId = $(cardElement).data("rihId");
    var hiddenInput = $("input#id_rulecard_" + rihId);
    if ($(cardElement).hasClass("card_selected")) {
        hiddenInput.val("False");
    } else {
        hiddenInput.val("True");
    }
    cardElement.toggleClass("card_selected");
    if (currentMode === "initial") {
        currentMode = "createTrade";
        $("#zone_tabs").tabs("option", "active", 1);
    }
    refreshSelectedRulecards();
}

$(".commodity_card").not(".not_tradable").on("click.tradecreate", function(event) {
    clickOnCommodity(event.target);
});
$(".rulecard").not(".not_tradable, .former").on("click.tradecreate", function(event) {
    clickOnRulecard($(event.target).closest(".rulecard"));
});

function prepareCardsInHandForSelection() {
    // mark as selected the cards in hand that are selected in the trade tab
    $("#zone_selected_commodities").find(".commodity_card").each(function() {
        $(correspondingCommodityInHand(this, false)).addClass("card_selected");
    });
    $("#zone_selected_rulecards").find(".rulecard_thumbnail").each(function() {
        $(correspondingRulecardInHand(this, false)).addClass("card_selected");
    });

    var allCommodities = $("#zone_commodities").find(".commodity_card");
    var allRulecards = $("#zone_rulecards").find(".rulecard");

    // mark as excluded the non tradable cards
    allCommodities.filter(".not_tradable").addClass("excluded").each(function() {
        $(this).attr("title", $(this).data("name") + " - Reserved for a pending trade");
    });
    allRulecards.filter(".not_tradable").addClass("excluded").children(".note")
        .text("(reserved for a pending trade)");

    // mark as selectable the tradable cards
    allCommodities.not(".not_tradable").addClass("selectable").off("click.tradecreate")
        .on("click.tradeselect", function(event) {
            clickOnCommodity(event.target)
        });
    allRulecards.not(".not_tradable, .former").addClass("selectable").off("click.tradecreate")
        .on("click.tradeselect", function(event) {
            clickOnRulecard($(event.target).closest(".rulecard")); // step up to the main div.rulecard if the click was on a sub-div
        });
}

function resetCardsInHandWhenSelectionIsDisabled() {
    var allCommodityCards = $("#zone_commodities").find(".commodity_card");
    var allRulecards = $("#zone_rulecards").find(".rulecard");

    // unmark the selectable cards
    allCommodityCards.not(".not_tradable").removeClass("card_selected selectable")
        .off("click.tradecreate").off("click.tradeselect");
    allRulecards.not(".not_tradable, .former").removeClass("card_selected selectable")
        .off("click.tradecreate").off("click.tradeselect");

    // unmark the non-tradable cards
    allCommodityCards.filter(".not_tradable").removeClass("excluded").each(function() {
        $(this).attr("title", $(this).data("name"));
    });
    allRulecards.filter(".not_tradable").removeClass("excluded").children(".note").text("");

    $(".click2createtrade").hide();
}

function eventClickOnATab(event, ui) {
    if ($(ui.newTab).attr("aria-controls") === "tab-trade") {
        $("form#new_offer").is(":visible") ?
            prepareCardsInHandForSelection() : resetCardsInHandWhenSelectionIsDisabled();
    } else {
        resetCardsInHandWhenSelectionIsDisabled();
    }
    setUpEventsRefreshIfTheEventsTabIsOpen();
}

function postTrade(tradeForm) {
    function replaceTradeId(tradeForm, url) {
        return url.replace('/0/', '/' + $(tradeForm).data("tradeId") + '/');
    }

    var url;
    switch($(tradeForm).data("tradeAction")) {
        case "create":
            url = "{% url 'create_trade' game.id %}";
            break;
        case "cancel":
            url = replaceTradeId(tradeForm, "{% url 'cancel_trade' game.id 0 %}");
            break;
        case "reply":
            url = replaceTradeId(tradeForm, "{% url 'reply_trade' game.id 0 %}");
            break;
        case "decline":
            url = replaceTradeId(tradeForm, "{% url 'decline_trade' game.id 0 %}");
            break;
        case "accept":
            url = replaceTradeId(tradeForm, "{% url 'accept_trade' game.id 0 %}");
            break;
    }
    $.post(url, $(tradeForm).serialize())
        .fail(function(jqXHR) {
            $("body").css("cursor", "");
            var tab_trade;
            if (jqXHR.status == 422) tab_trade = jqXHR.responseText;
            else tab_trade = "Error sending data. Please try again.";
            $("#zone_trade").html(tab_trade);
            refreshSelectedCommodities(); // re-display cards in the trade tab
            refreshSelectedRulecards();
        })
        .done(function() {
            window.location.reload(true);
        });
    $("body").css("cursor", "wait");
    $(tradeForm).find(":input").prop("disabled", true);
    $(tradeForm).find(".selectable").off("click.tradeselect");
}

$("#link_new_trade").on("click", function() {
    if (currentMode === "editTrade") {
        $("#zone_trade").text("Loading...");
        $("#zone_tabs").find("li[aria-controls=tab-trade]").find("a").text("New Trade");
        refreshTrade();
        resetCardsInHandWhenSelectionIsDisabled();
    }
    $("#zone_tabs").tabs("option", "active", 1);
    currentMode = "createTrade";
});